from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import FriendRequest, Friendship, Notification, Profile, get_profile, xp_required_for_level
from game.models import Pen, PenSkin


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.profile = get_profile(self.user)

    def test_profile_auto_created_on_user_creation(self):
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.level, 1)
        self.assertEqual(self.profile.pen_points, 250)

    def test_xp_required_for_level(self):
        self.assertEqual(xp_required_for_level(1), 400)
        self.assertEqual(xp_required_for_level(2), 520)

    def test_add_xp_and_level_up(self):
        levels_gained = self.profile.add_xp(450)
        self.assertEqual(levels_gained, [2])
        self.assertEqual(self.profile.level, 2)
        self.assertEqual(self.profile.xp, 50)

    def test_win_rate_calculation(self):
        self.assertEqual(self.profile.win_rate, 0.0)
        self.profile.wins = 3
        self.profile.losses = 1
        self.assertEqual(self.profile.win_rate, 75.0)

    def test_register_match_result_win_and_loss(self):
        self.profile.register_match_result(won=True, knockout=True)
        self.assertEqual(self.profile.matches_played, 1)
        self.assertEqual(self.profile.wins, 1)
        self.assertEqual(self.profile.rating, 25)
        self.assertEqual(self.profile.current_win_streak, 1)
        self.assertEqual(self.profile.best_win_streak, 1)
        self.assertEqual(self.profile.knockouts, 1)

        self.profile.register_match_result(won=False)
        self.assertEqual(self.profile.matches_played, 2)
        self.assertEqual(self.profile.losses, 1)
        self.assertEqual(self.profile.rating, 10)
        self.assertEqual(self.profile.current_win_streak, 0)
        self.assertEqual(self.profile.best_win_streak, 1)

    def test_recalc_rank(self):
        self.profile.rating = 650
        self.profile.recalc_rank()
        self.assertEqual(self.profile.rank_tier, "silver")

        self.profile.rating = 1850
        self.profile.recalc_rank()
        self.assertEqual(self.profile.rank_tier, "platinum")


class FriendshipModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        self.user3 = User.objects.create_user(username="user3", password="password123")

    def test_are_friends_and_friends_of(self):
        self.assertFalse(Friendship.are_friends(self.user1, self.user2))
        a, b = sorted([self.user1.id, self.user2.id])
        Friendship.objects.create(user_a_id=a, user_b_id=b)

        self.assertTrue(Friendship.are_friends(self.user1, self.user2))
        self.assertTrue(Friendship.are_friends(self.user2, self.user1))

        friends = list(Friendship.friends_of(self.user1))
        self.assertEqual(len(friends), 1)
        self.assertEqual(friends[0], self.user2)

    def test_friend_request_accept_and_decline(self):
        req = FriendRequest.objects.create(from_user=self.user1, to_user=self.user2)
        self.assertEqual(req.status, "pending")

        req.accept()
        self.assertEqual(req.status, "accepted")
        self.assertTrue(Friendship.are_friends(self.user1, self.user2))
        self.assertTrue(Notification.objects.filter(user=self.user1, notif_type="friend_accepted").exists())

        req2 = FriendRequest.objects.create(from_user=self.user1, to_user=self.user3)
        req2.decline()
        self.assertEqual(req2.status, "declined")
        self.assertFalse(Friendship.are_friends(self.user1, self.user3))


class AccountsViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="player1", password="password123")
        self.other = User.objects.create_user(username="player2", password="password123")

    def test_signup_view_get_and_post(self):
        res = self.client.get(reverse("accounts:signup"))
        self.assertEqual(res.status_code, 200)

        post_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "Password123!",
            "password2": "Password123!",
        }
        res_post = self.client.post(reverse("accounts:signup"), post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_dashboard_view_requires_login(self):
        res = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(res.status_code, 302)

        self.client.login(username="player1", password="password123")
        res_auth = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(res_auth.status_code, 200)
        self.assertIn("profile", res_auth.context)

    def test_profile_detail_view(self):
        url = reverse("accounts:profile", args=["player1"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["profile_user"], self.user)

    def test_profile_edit_view(self):
        self.client.login(username="player1", password="password123")
        res = self.client.post(reverse("accounts:profile_edit"), {"bio": "New Bio Text"})
        self.assertEqual(res.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, "New Bio Text")

    def test_leaderboard_view(self):
        self.client.login(username="player1", password="password123")
        res = self.client.get(reverse("accounts:leaderboard"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("profiles", res.context)

    def test_send_and_respond_friend_request_flow(self):
        self.client.login(username="player1", password="password123")
        res = self.client.post(reverse("accounts:send_friend_request", args=["player2"]))
        self.assertEqual(res.status_code, 302)

        fr = FriendRequest.objects.get(from_user=self.user, to_user=self.other)
        self.assertEqual(fr.status, "pending")

        self.client.login(username="player2", password="password123")
        res_accept = self.client.post(reverse("accounts:respond_friend_request", args=[fr.id, "accept"]))
        self.assertEqual(res_accept.status_code, 302)
        self.assertTrue(Friendship.are_friends(self.user, self.other))

    def test_mark_notifications_read(self):
        notif = Notification.objects.create(
            user=self.user, notif_type="achievement", message="Test Notif", link="/accounts/dashboard/"
        )
        self.client.login(username="player1", password="password123")
        res = self.client.post(reverse("accounts:mark_notification_read", args=[notif.id]))
        self.assertEqual(res.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
