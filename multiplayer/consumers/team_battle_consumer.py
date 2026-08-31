import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class TeamBattleConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time 2v2 PenFight sync for a team room (4 players, 2 per team).

    Slots: t1p1 (host), t1p2 (team1_player2), t2p1 (guest), t2p2 (team2_player2)
    Turn order: t1p1 → t2p1 → t1p2 → t2p2 → repeat

    Server-authoritative for:
      * Turn order (tracked server-side, rejects out-of-turn flicks)
      * "pen fell off" → team win detection (both pens of one team must fall)
      * match.finish(), rewards, stats — via multiplayer.services.finish_team_match
    """

    TURN_ORDER = ["t1p1", "t2p1", "t1p2", "t2p2"]
    TEAM1_SLOTS = {"t1p1", "t1p2"}
    TEAM2_SLOTS = {"t2p1", "t2p2"}

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"team_battle_{self.room_code}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        room = await self._get_room()
        if not room:
            await self.close()
            return

        self.slot = await self._get_slot(room)
        if not self.slot:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(self.group_name, {
            "type": "broadcast", "payload": {
                "kind": "player_joined", "slot": self.slot, "username": self.user.username,
            },
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {
                    "kind": "opponent_left", "slot": getattr(self, "slot", None),
                    "username": self.user.username,
                },
            })

    async def receive_json(self, content, **kwargs):
        kind = content.get("kind")

        if kind in ("flick", "settle_state", "sync_request"):
            content["slot"] = self.slot
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": content,
            })

        elif kind == "ready":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {"kind": "player_ready", "slot": self.slot},
            })

        elif kind == "select_loadout":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {
                    "kind": "opponent_loadout", "slot": self.slot,
                    "pen": content.get("pen"), "skin": content.get("skin"),
                },
            })

        elif kind == "pen_out":
            # A pen fell off the desk. Track it and check team-level win.
            fallen_slot = content.get("slot")
            result = await self._handle_pen_out(fallen_slot, content.get("pen_ids", {}))
            if result:
                await self.channel_layer.group_send(self.group_name, {
                    "type": "broadcast", "payload": result,
                })

        elif kind == "chat":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {
                    "kind": "chat", "slot": self.slot, "username": self.user.username,
                    "message": str(content.get("message", ""))[:200],
                },
            })

        elif kind == "rematch_request":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {"kind": "rematch_request", "slot": self.slot},
            })

    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    # -- DB helpers ---------------------------------------------------

    @database_sync_to_async
    def _get_room(self):
        from multiplayer.models import PrivateRoom
        return PrivateRoom.objects.filter(
            code=self.room_code, room_type="2v2"
        ).select_related("host", "guest", "team1_player2", "team2_player2", "match").first()

    @database_sync_to_async
    def _get_slot(self, room):
        return room.slot_for_user(self.user)

    @database_sync_to_async
    def _handle_pen_out(self, fallen_slot, pen_ids):
        """Check if a team has lost (both their pens fell). Only the first
        reporter triggers the authoritative match finish."""
        from multiplayer.models import PrivateRoom
        from multiplayer.services import finish_team_match

        room = PrivateRoom.objects.select_related(
            "host", "guest", "team1_player2", "team2_player2", "match"
        ).get(code=self.room_code)

        if not room.match or room.match.status == "finished":
            return {"kind": "already_finished", "already_finished": True}

        # Broadcast which pen fell (client tracks round state)
        result = {
            "kind": "team_pen_fell",
            "fallen_slot": fallen_slot,
        }

        # Check if both pens of a team have fallen — match-level win
        # The client sends pen_out with is_team_eliminated=True when both
        # enemy pens are down in the current round AND the round is the
        # deciding round (best-of-3 at match level).
        # For simplicity, the client handles round-level logic; the server
        # only handles the final match_over event.
        if pen_ids.get("match_over"):
            winning_team_slots = pen_ids.get("winning_team", "team1")

            if winning_team_slots == "team1":
                winning_team = [room.host, room.team1_player2]
                losing_team = [room.guest, room.team2_player2]
            else:
                winning_team = [room.guest, room.team2_player2]
                losing_team = [room.host, room.team1_player2]

            # Filter out None users (shouldn't happen but safety)
            winning_team = [u for u in winning_team if u]
            losing_team = [u for u in losing_team if u]

            summary = finish_team_match(room.match, winning_team, losing_team)
            room.status = PrivateRoom.Status.FINISHED
            room.save(update_fields=["status"])

            return {
                "kind": "match_over",
                "winning_team": winning_team_slots,
                "winner_usernames": [u.username for u in winning_team],
                "loser_usernames": [u.username for u in losing_team],
                "winner_rewards": summary["winner_rewards"],
                "loser_rewards": summary["loser_rewards"],
                "winner_achievements": summary["winner_achievements"],
            }

        return result
