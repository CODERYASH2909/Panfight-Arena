import json
import asyncio
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BattleConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time PenFight sync for private room lobby & in-game battle (2-5 players).
    Handles lobby connection, ready state toggling, start countdown, and battle physics sync.
    """
    ROOM_READY_STATES = {}

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"battle_{self.room_code}"
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

        if self.room_code not in BattleConsumer.ROOM_READY_STATES:
            BattleConsumer.ROOM_READY_STATES[self.room_code] = {}

        ready_states = BattleConsumer.ROOM_READY_STATES[self.room_code]
        if self.slot not in ready_states:
            ready_states[self.slot] = False

        players_info = await self._get_players_info(room)

        await self.channel_layer.group_send(self.group_name, {
            "type": "broadcast",
            "payload": {
                "kind": "player_joined",
                "slot": self.slot,
                "username": self.user.username,
                "max_players": room.max_players,
                "current_players": room.player_count,
                "players": players_info,
                "ready_states": ready_states,
            },
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            room = await self._get_room()
            players_info = await self._get_players_info(room) if room else []
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast",
                "payload": {
                    "kind": "opponent_left",
                    "slot": getattr(self, "slot", None),
                    "username": getattr(self.user, "username", "Player"),
                    "players": players_info,
                },
            })

    async def receive_json(self, content, **kwargs):
        kind = content.get("kind")

        if kind in ("flick", "settle_state", "sync_request"):
            content["slot"] = self.slot
            await self.channel_layer.group_send(self.group_name, {"type": "broadcast", "payload": content})

        elif kind in ("ready", "toggle_ready"):
            ready_states = BattleConsumer.ROOM_READY_STATES.setdefault(self.room_code, {})
            ready_states[self.slot] = not ready_states.get(self.slot, False)

            room = await self._get_room()
            players_info = await self._get_players_info(room) if room else []
            active_slots = [p["slot"] for p in players_info]

            all_ready = len(active_slots) >= 2 and all(ready_states.get(s, False) for s in active_slots)

            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast",
                "payload": {
                    "kind": "player_ready_state",
                    "slot": self.slot,
                    "ready": ready_states[self.slot],
                    "ready_states": ready_states,
                    "all_ready": all_ready,
                },
            })

            if all_ready:
                await self._start_battle_match()
                await self.channel_layer.group_send(self.group_name, {
                    "type": "broadcast", "payload": {"kind": "start_countdown", "seconds": 3},
                })

        elif kind == "select_loadout":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast",
                "payload": {
                    "kind": "opponent_loadout",
                    "slot": self.slot,
                    "pen": content.get("pen"),
                    "skin": content.get("skin"),
                },
            })

        elif kind == "pen_out":
            winner_slot = content.get("winner_slot")
            loser_slot = content.get("slot")
            result = await self._resolve_match(winner_slot, loser_slot, content.get("pen_ids", {}))
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {"kind": "match_over", **result},
            })

        elif kind == "chat":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast",
                "payload": {
                    "kind": "chat",
                    "slot": self.slot,
                    "username": self.user.username,
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
        return PrivateRoom.objects.filter(code=self.room_code).select_related("host", "guest", "player3", "player4", "player5", "match").first()

    @database_sync_to_async
    def _get_slot(self, room):
        return room.slot_for_user(self.user)

    @database_sync_to_async
    def _get_players_info(self, room):
        if not room:
            return []
        info = []
        for i in range(1, room.max_players + 1):
            slot_key = f"player{i}"
            user = room.get_user_by_slot(slot_key)
            if user:
                info.append({
                    "slot": slot_key,
                    "username": user.username,
                    "is_host": (user == room.host),
                })
        return info

    @database_sync_to_async
    def _start_battle_match(self):
        from multiplayer.models import PrivateRoom, Match
        room = PrivateRoom.objects.filter(code=self.room_code).first()
        if room:
            if not room.match:
                match = Match.objects.create(
                    match_type=Match.MatchType.PRIVATE,
                    arena=room.arena,
                    status=Match.Status.IN_PROGRESS,
                    room_code=room.code,
                )
                room.match = match
            room.status = PrivateRoom.Status.IN_PROGRESS
            room.save(update_fields=["match", "status"])
            return room.match

    @database_sync_to_async
    def _resolve_match(self, winner_slot, loser_slot, pen_ids):
        from game.models import Pen, PenSkin
        from multiplayer.models import PrivateRoom
        from multiplayer.services import finish_online_match

        room = PrivateRoom.objects.select_related("host", "guest", "player3", "player4", "player5", "match").get(code=self.room_code)
        if not room.match or room.match.status == "finished":
            return {"already_finished": True}

        winner_user = room.get_user_by_slot(winner_slot) if winner_slot else None
        if not winner_user:
            # Fallback to non-loser player
            all_players = room.all_players
            loser_user = room.get_user_by_slot(loser_slot)
            survivors = [p for p in all_players if p != loser_user]
            winner_user = survivors[0] if survivors else room.host
            winner_slot = room.slot_for_user(winner_user)

        loser_user = room.get_user_by_slot(loser_slot) or (room.guest if winner_user == room.host else room.host)

        def _lookup(model, pk):
            return model.objects.filter(id=pk).first() if pk else None

        summary = finish_online_match(
            room.match, winner_user, loser_user,
            winner_pen=_lookup(Pen, pen_ids.get(f"{winner_slot}_pen")),
            winner_skin=_lookup(PenSkin, pen_ids.get(f"{winner_slot}_skin")),
            loser_pen=_lookup(Pen, pen_ids.get(f"{loser_slot}_pen")),
            loser_skin=_lookup(PenSkin, pen_ids.get(f"{loser_slot}_skin")),
        )
        room.status = PrivateRoom.Status.FINISHED
        room.save(update_fields=["status"])

        return {
            "winner_slot": winner_slot,
            "winner_username": winner_user.username,
            "loser_username": loser_user.username,
            "winner_rewards": summary["winner_rewards"],
            "loser_rewards": summary["loser_rewards"],
            "winner_achievements": summary["winner_achievements"],
        }

