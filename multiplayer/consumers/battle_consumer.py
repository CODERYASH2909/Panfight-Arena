import json
import asyncio
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BattleConsumer(AsyncJsonWebsocketConsumer):
    """
    Real-time PenFight sync for private room lobby & in-game battle.
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
        if not room or self.user.id not in [room.host_id, room.guest_id]:
            await self.close()
            return

        self.slot = "player1" if room.host_id == self.user.id else "player2"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        if self.room_code not in BattleConsumer.ROOM_READY_STATES:
            BattleConsumer.ROOM_READY_STATES[self.room_code] = {"player1": False, "player2": False}

        ready_state = BattleConsumer.ROOM_READY_STATES[self.room_code]

        await self.channel_layer.group_send(self.group_name, {
            "type": "broadcast", "payload": {
                "kind": "player_joined",
                "slot": self.slot,
                "username": self.user.username,
                "host_username": room.host.username,
                "guest_username": room.guest.username if room.guest else None,
                "p1_ready": ready_state["player1"],
                "p2_ready": ready_state["player2"],
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
            content["slot"] = self.slot
            await self.channel_layer.group_send(self.group_name, {"type": "broadcast", "payload": content})

        elif kind in ("ready", "toggle_ready"):
            ready_state = BattleConsumer.ROOM_READY_STATES.setdefault(self.room_code, {"player1": False, "player2": False})
            ready_state[self.slot] = not ready_state.get(self.slot, False)

            p1_ready = ready_state["player1"]
            p2_ready = ready_state["player2"]

            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {
                    "kind": "player_ready_state",
                    "slot": self.slot,
                    "ready": ready_state[self.slot],
                    "p1_ready": p1_ready,
                    "p2_ready": p2_ready,
                },
            })

            # When both players are ready, trigger match start countdown
            if p1_ready and p2_ready:
                await self._start_battle_match()
                await self.channel_layer.group_send(self.group_name, {
                    "type": "broadcast", "payload": {"kind": "start_countdown", "seconds": 3},
                })

        elif kind == "select_loadout":
            await self.channel_layer.group_send(self.group_name, {
                "type": "broadcast", "payload": {
                    "kind": "opponent_loadout", "slot": self.slot,
                    "pen": content.get("pen"), "skin": content.get("skin"),
                },
            })

        elif kind == "pen_out":
            loser_slot = content.get("slot")
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
    def _resolve_match(self, loser_slot, pen_ids):
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
