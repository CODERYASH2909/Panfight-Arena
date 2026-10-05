from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import Notification, get_profile
from game.models import Achievement, UserAchievement
from rewards.models import PenPointTransaction
from rewards.services import (
    apply_match_result_rewards,
    check_achievements,
    grant_daily_reward_if_eligible,
    grant_pen_points,
    grant_xp,
    has_enough_pp,
)


class RewardsServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reward_user", password="password123")
        self.profile = get_profile(self.user)

    def test_grant_pen_points_positive_and_negative(self):
        initial_pp = self.profile.pen_points
        tx1 = grant_pen_points(self.user, 100, PenPointTransaction.Reason.MATCH_WIN, note="Test Win")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pen_points, initial_pp + 100)
        self.assertEqual(tx1.amount, 100)
        self.assertEqual(tx1.balance_after, initial_pp + 100)
        self.assertEqual(tx1.reason, PenPointTransaction.Reason.MATCH_WIN)

        tx2 = grant_pen_points(self.user, -50, PenPointTransaction.Reason.STORE_PURCHASE, note="Test Buy")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pen_points, initial_pp + 50)
        self.assertEqual(tx2.amount, -50)

    def test_has_enough_pp(self):
        self.profile.pen_points = 200
        self.profile.save()
        self.user.refresh_from_db()
        self.assertTrue(has_enough_pp(self.user, 150))
        self.assertTrue(has_enough_pp(self.user, 200))
        self.assertFalse(has_enough_pp(self.user, 201))

    def test_grant_xp_level_up(self):
        # 1st level requires 400 XP
        levels = grant_xp(self.user, 450)
        self.assertEqual(levels, [2])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.level, 2)
        self.assertTrue(Notification.objects.filter(user=self.user, notif_type="level_up").exists())

    def test_apply_match_result_rewards_win_and_loss(self):
        res_win = apply_match_result_rewards(self.user, won=True, win_streak=3)
        self.assertEqual(res_win["pp"], 100)
        self.assertEqual(res_win["xp"], 120)
        self.assertEqual(res_win["streak_bonus"], 50)

        res_loss = apply_match_result_rewards(self.user, won=False)
        self.assertEqual(res_loss["pp"], 25)
        self.assertEqual(res_loss["xp"], 40)
        self.assertEqual(res_loss["streak_bonus"], 0)

    def test_grant_daily_reward_if_eligible(self):
        payout1 = grant_daily_reward_if_eligible(self.user)
        self.assertEqual(payout1, 25)

        # Immediate second try should return None (already claimed today)
        payout2 = grant_daily_reward_if_eligible(self.user)
        self.assertIsNone(payout2)

    def test_check_achievements(self):
        ach = Achievement.objects.create(
            key="first_win",
            name="First Win",
            description="Win 1 match",
            reward_pp=50,
            reward_xp=100,
            target_stat="wins",
            target_value=1,
        )
        # Not unlocked yet
        newly_unlocked = check_achievements(self.user)
        self.assertEqual(len(newly_unlocked), 0)

        # Grant 1 win
        self.profile.wins = 1
        self.profile.save()
        self.user.refresh_from_db()

        newly_unlocked = check_achievements(self.user)
        self.assertEqual(len(newly_unlocked), 1)
        self.assertEqual(newly_unlocked[0], ach)
        self.assertTrue(UserAchievement.objects.filter(user=self.user, achievement=ach).exists())

        # Checking again does not re-trigger unlock
        newly_unlocked_again = check_achievements(self.user)
        self.assertEqual(len(newly_unlocked_again), 0)
