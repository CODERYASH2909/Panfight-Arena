from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from channels.testing import WebsocketCommunicator

from accounts.models import Notification, get_profile
from game.models import Arena, Pen, PenSkin
from multiplayer.models import Match, MatchPlayer, MatchmakingTicket, PrivateRoom
from multiplayer.services import finish_online_match, try_pair_quick_match
from penfight.asgi import application


class MultiplayerServicesAndModelsTest(TestCase):
    def setUp(self):
        call_command("seed_penfight")
        self.user1 = User.objects.create_user(username="host", password="password123")
        self.user2 = User.objects.create_user(username="guest", password="password123")
        self.arena = Arena.objects.first()

    def test_private_room_slots_and_players(self):
        room = PrivateRoom.objects.create(host=self.user1, arena=self.arena, max_players=2)
        self.assertEqual(room.player_count, 1)
        self.assertFalse(room.is_full)
        self.assertEqual(room.slot_for_user(self.user1), "player1")

        added = room.add_player(self.user2)
        self.assertTrue(added)
        self.assertEqual(room.player_count, 2)
        self.assertTrue(room.is_full)
        self.assertEqual(room.slot_for_user(self.user2), "player2")
        self.assertEqual(room.get_user_by_slot("player2"), self.user2)

    def test_try_pair_quick_match(self):
        t1 = MatchmakingTicket.objects.create(user=self.user1, rating_at_time=100)
        t2 = MatchmakingTicket.objects.create(user=self.user2, rating_at_time=150)

        room = try_pair_quick_match(t1)
        self.assertIsNotNone(room)
        self.assertEqual(t1.refresh_from_db() or t1.status, MatchmakingTicket.Status.MATCHED)
        self.assertEqual(t2.refresh_from_db() or t2.status, MatchmakingTicket.Status.MATCHED)
        self.assertEqual(room.host, self.user2)
        self.assertEqual(room.guest, self.user1)

    def test_finish_online_match_service(self):
        match = Match.objects.create(match_type=Match.MatchType.QUICK, arena=self.arena)
        res = finish_online_match(match, winner_user=self.user1, loser_user=self.user2)

        match.refresh_from_db()
        self.assertEqual(match.status, Match.Status.FINISHED)
        self.assertEqual(match.winner, self.user1)
        self.assertIn("winner_rewards", res)
        self.assertIn("loser_rewards", res)
        self.assertTrue(MatchPlayer.objects.filter(match=match, user=self.user1, is_winner=True).exists())
        self.assertTrue(MatchPlayer.objects.filter(match=match, user=self.user2, is_winner=False).exists())


class MultiplayerViewsTest(TestCase):
    def setUp(self):
        call_command("seed_penfight")
        self.user1 = User.objects.create_user(username="playerA", password="password123")
        self.user2 = User.objects.create_user(username="playerB", password="password123")
        self.arena = Arena.objects.first()

    def test_create_and_join_room_views(self):
        self.client.login(username="playerA", password="password123")
        res_create = self.client.post(reverse("multiplayer:room_create"), {"max_players": 2})
        self.assertEqual(res_create.status_code, 302)

        room = PrivateRoom.objects.filter(host=self.user1).first()
        self.assertIsNotNone(room)

        # Join view by playerB
        self.client.login(username="playerB", password="password123")
        res_join = self.client.post(reverse("multiplayer:room_join"), {"code": room.code})
        self.assertEqual(res_join.status_code, 302)
        room.refresh_from_db()
        self.assertEqual(room.guest, self.user2)

    def test_room_lobby_and_status_api(self):
        room = PrivateRoom.objects.create(host=self.user1, arena=self.arena, max_players=2)
        self.client.login(username="playerA", password="password123")

        res_lobby = self.client.get(reverse("multiplayer:room_lobby", args=[room.code]))
        self.assertEqual(res_lobby.status_code, 200)

        res_status = self.client.get(reverse("multiplayer:room_status", args=[room.code]))
        self.assertEqual(res_status.status_code, 200)
        data = res_status.json()
        self.assertTrue(data["exists"])
        self.assertEqual(data["current_players"], 1)

    def test_room_start_view(self):
        room = PrivateRoom.objects.create(host=self.user1, guest=self.user2, arena=self.arena, max_players=2)
        self.client.login(username="playerA", password="password123")

        res_start = self.client.post(reverse("multiplayer:room_start", args=[room.code]))
        self.assertEqual(res_start.status_code, 302)
        room.refresh_from_db()
        self.assertEqual(room.status, PrivateRoom.Status.IN_PROGRESS)
        self.assertIsNotNone(room.match)

    def test_quick_match_views_flow(self):
        self.client.login(username="playerA", password="password123")
        res_page = self.client.get(reverse("multiplayer:quick_match"))
        self.assertEqual(res_page.status_code, 200)

        res_start = self.client.post(reverse("multiplayer:quick_match_start"))
        self.assertEqual(res_start.status_code, 200)
        self.assertFalse(res_start.json()["matched"])

        res_poll = self.client.get(reverse("multiplayer:quick_match_poll"))
        self.assertEqual(res_poll.status_code, 200)

        res_cancel = self.client.post(reverse("multiplayer:quick_match_cancel"))
        self.assertEqual(res_cancel.status_code, 200)
        self.assertTrue(res_cancel.json()["ok"])

    def test_challenge_friend_flow(self):
        self.client.login(username="playerA", password="password123")
        res_chal = self.client.post(reverse("multiplayer:challenge_friend", args=["playerB"]))
        self.assertEqual(res_chal.status_code, 302)

        room = PrivateRoom.objects.filter(host=self.user1, guest=self.user2).first()
        self.assertIsNotNone(room)
        self.assertTrue(Notification.objects.filter(user=self.user2, notif_type="challenge").exists())

        self.client.login(username="playerB", password="password123")
        res_accept = self.client.get(reverse("multiplayer:accept_challenge", args=[room.code]))
        self.assertEqual(res_accept.status_code, 302)
        room.refresh_from_db()
        self.assertEqual(room.status, PrivateRoom.Status.READY)


class BattleConsumerWebSocketTest(TestCase):
    def setUp(self):
        call_command("seed_penfight")
        self.user1 = User.objects.create_user(username="wsuser1", password="password123")
        self.user2 = User.objects.create_user(username="wsuser2", password="password123")
        self.arena = Arena.objects.first()
        self.room = PrivateRoom.objects.create(
            host=self.user1, guest=self.user2, arena=self.arena, max_players=2
        )

    async def test_websocket_connect_and_broadcast(self):
        communicator = WebsocketCommunicator(
            application, f"/ws/battle/{self.room.code}/",
            headers=[(b"origin", b"http://127.0.0.1:8000")]
        )
        communicator.scope["user"] = self.user1
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await communicator.receive_json_from()
        self.assertEqual(response["kind"], "player_joined")
        self.assertEqual(response["slot"], "player1")

        # Send chat message
        await communicator.send_json_to({"kind": "chat", "message": "Hello world!"})
        msg_resp = await communicator.receive_json_from()
        self.assertEqual(msg_resp["kind"], "chat")
        self.assertEqual(msg_resp["message"], "Hello world!")

        await communicator.disconnect()
