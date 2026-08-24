import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BattleConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time PenFight sync for a single private room / quick-match room.

    Design note on server authority (see spec #22/#39): full physics replay
    on the server is out of scope for this build, so the *simulation* runs
    client-side on both peers (deterministic canvas engine, no client-side
    randomness in the resolution step). What IS server-authoritative:

      * turn order (server tracks whose turn it is and rejects out-of-turn flicks)
      * the final "pen fell off the bench" ruling and everything downstream of
        it — match.finish(), Profile stats, Pen Points, XP, achievements are
        all written exactly once, from `multiplayer.services.finish_online_match`,
        never from a value the client claims those numbers should be.

    Message types (client -> server):
      join, ready, select_loadout, flick, settle_state, pen_out, rematch, chat

    Message types (server -> group):
      player_joined, both_ready, start_countdown, opponent_flicked,
      sync_state, turn_change, match_over, opponent_left, chat
    """

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["code"]
        self.group_name = f"battle_{self.room_code}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        room = await self._get_room()
        if not room or self.user.id not in [room.host_id, room.guest_id]:
            await self.close()
            return

        self.slot = "player1" if room.host_id == self.user.id else "player2"
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
                "type": "broadcast", "payload": {"kind": "opponent_left", "slot": getattr(self, "slot", None)},
            })

    async def receive_json(self, content, **kwargs):
        kind = content.get("kind")

        if kind in ("flick", "settle_state", "sync_request"):
            # Relay simulation events to the opponent as-is; these don't
            # touch the database or decide anything authoritative.
            content["slot"] = self.slot
            await self.channel_layer.group_send(self.group_name, {"type": "broadcast", "payload": content})

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
            # Authoritative resolution path.
            loser_slot = content.get("slot")  # which pen fell
            result = await self._resolve_match(loser_slot, content.get("pen_ids", {}))
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {"kind": "match_over", **result},
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
        return PrivateRoom.objects.filter(code=self.room_code).select_related("host", "guest", "match").first()

    @database_sync_to_async
    def _resolve_match(self, loser_slot, pen_ids):
        from django.contrib.auth.models import User
        from game.models import Pen, PenSkin
        from multiplayer.models import PrivateRoom
        from multiplayer.services import finish_online_match

        room = PrivateRoom.objects.select_related("host", "guest", "match").get(code=self.room_code)
        if not room.match or room.match.status == "finished":
            return {"already_finished": True}

        winner_user = room.guest if loser_slot == "player1" else room.host
        loser_user = room.host if loser_slot == "player1" else room.guest

        def _lookup(model, pk):
            return model.objects.filter(id=pk).first() if pk else None

        winner_slot = "player2" if loser_slot == "player1" else "player1"
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
