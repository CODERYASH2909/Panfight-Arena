from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import get_profile
from game.models import PenInventory, PenSkin
from rewards.models import PenPointTransaction
from store.models import StorePurchase
from store.services import purchase_skin


class StoreServicesAndViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shopper", password="password123")
        self.profile = get_profile(self.user)
        self.profile.pen_points = 500
        self.profile.save()

        self.skin_affordable = PenSkin.objects.create(
            name="Neon Cyber",
            price_pp=200,
            is_purchasable=True,
            is_featured=True,
        )
        self.skin_expensive = PenSkin.objects.create(
            name="Golden Royal",
            price_pp=1000,
            is_purchasable=True,
        )
        self.skin_locked = PenSkin.objects.create(
            name="Event Exclusive",
            price_pp=100,
            is_purchasable=False,
        )

    def test_purchase_skin_success(self):
        res = purchase_skin(self.user, self.skin_affordable)
        self.assertTrue(res.success)
        self.assertEqual(res.error, "")
        self.assertTrue(PenInventory.objects.filter(user=self.user, skin=self.skin_affordable).exists())
        self.assertTrue(StorePurchase.objects.filter(user=self.user, skin=self.skin_affordable).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.pen_points, 300)
        self.assertTrue(
            PenPointTransaction.objects.filter(
                user=self.user, reason=PenPointTransaction.Reason.STORE_PURCHASE
            ).exists()
        )

    def test_purchase_skin_insufficient_pp(self):
        res = purchase_skin(self.user, self.skin_expensive)
        self.assertFalse(res.success)
        self.assertEqual(res.error, "Not enough Pen Points.")
        self.assertFalse(PenInventory.objects.filter(user=self.user, skin=self.skin_expensive).exists())

    def test_purchase_skin_already_owned(self):
        purchase_skin(self.user, self.skin_affordable)
        res_again = purchase_skin(self.user, self.skin_affordable)
        self.assertFalse(res_again.success)
        self.assertEqual(res_again.error, "You already own this skin.")

    def test_purchase_skin_not_purchasable(self):
        res = purchase_skin(self.user, self.skin_locked)
        self.assertFalse(res.success)
        self.assertEqual(res.error, "This skin isn't available in the store right now.")

    def test_store_views(self):
        self.client.login(username="shopper", password="password123")
        res = self.client.get(reverse("store:home"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("featured", res.context)

        # POST buy skin
        res_buy = self.client.post(reverse("store:buy_skin", args=[self.skin_affordable.id]))
        self.assertEqual(res_buy.status_code, 302)
        self.assertTrue(PenInventory.objects.filter(user=self.user, skin=self.skin_affordable).exists())
