import json
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import get_profile
from game.models import Achievement, Arena, Pen, PenInventory, PenSkin, UserAchievement
from game.services import grant_starter_kit


class GameServicesAndModelsTest(TestCase):
    def setUp(self):
        call_command("seed_penfight")
        self.user = User.objects.create_user(username="gamer", password="password123")
        self.profile = get_profile(self.user)

    def test_starter_kit_granted(self):
        grant_starter_kit(self.user)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.equipped_pen)
        self.assertIsNotNone(self.profile.equipped_skin)
        self.assertIsNotNone(self.profile.favorite_arena)
        self.assertTrue(PenInventory.objects.filter(user=self.user, skin=self.profile.equipped_skin).exists())

    def test_seed_penfight_command_is_idempotent(self):
        call_command("seed_penfight")
        self.assertGreater(Pen.objects.count(), 0)
        self.assertGreater(PenSkin.objects.count(), 0)
        self.assertGreater(Arena.objects.count(), 0)
        self.assertGreater(Achievement.objects.count(), 0)


class GameViewsTest(TestCase):
    def setUp(self):
        call_command("seed_penfight")
        self.user = User.objects.create_user(username="gamer1", password="password123")
        self.profile = get_profile(self.user)
        grant_starter_kit(self.user)

    def test_landing_and_how_it_works_pages(self):
        res_landing = self.client.get(reverse("game:landing"))
        self.assertEqual(res_landing.status_code, 200)

        res_how = self.client.get(reverse("game:how_it_works"))
        self.assertEqual(res_how.status_code, 200)

    def test_my_pen_view_and_loadout_change(self):
        self.client.login(username="gamer1", password="password123")
        res = self.client.get(reverse("game:my_pen"))
        self.assertEqual(res.status_code, 200)

        # Equip starter pen + skin
        pen = Pen.objects.first()
        skin = self.profile.equipped_skin
        res_change = self.client.post(reverse("game:my_pen"), {"pen_id": pen.id, "skin_id": skin.id})
        self.assertEqual(res_change.status_code, 302)

        # Try to equip an unowned skin
        unowned_skin = PenSkin.objects.exclude(id=skin.id).first()
        if unowned_skin:
            res_fail = self.client.post(reverse("game:my_pen"), {"pen_id": pen.id, "skin_id": unowned_skin.id})
            self.assertEqual(res_fail.status_code, 302)

    def test_collection_view(self):
        self.client.login(username="gamer1", password="password123")
        res = self.client.get(reverse("game:collection"))
        self.assertEqual(res.status_code, 200)

    def test_local_battle_flow(self):
        self.client.login(username="gamer1", password="password123")
        res_setup = self.client.get(reverse("game:local_setup"))
        self.assertEqual(res_setup.status_code, 200)

        res_play = self.client.get(reverse("game:local_play") + "?arena=classic-classroom")
        self.assertEqual(res_play.status_code, 200)

        # Post result
        res_result = self.client.post(
            reverse("game:local_result"),
            data=json.dumps({"winner": "player1"}),
            content_type="application/json",
        )
        self.assertEqual(res_result.status_code, 200)
        data = res_result.json()
        self.assertTrue(data["ok"])
        self.assertIn("rewards", data)

    def test_ai_battle_flow(self):
        self.client.login(username="gamer1", password="password123")
        res_setup = self.client.get(reverse("game:ai_setup"))
        self.assertEqual(res_setup.status_code, 200)

        res_play = self.client.get(reverse("game:ai_play") + "?arena=classic-classroom")
        self.assertEqual(res_play.status_code, 200)

        res_result = self.client.post(
            reverse("game:ai_result"),
            data=json.dumps({"winner": "player1"}),
            content_type="application/json",
        )
        self.assertEqual(res_result.status_code, 200)
        data = res_result.json()
        self.assertTrue(data["ok"])

    def test_achievements_view(self):
        self.client.login(username="gamer1", password="password123")
        res = self.client.get(reverse("game:achievements"))
        self.assertEqual(res.status_code, 200)
