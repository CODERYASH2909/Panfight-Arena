from django.conf import settings
from django.db import models


class StorePurchase(models.Model):
    """Record of a cosmetic purchase. Existence of this row + the matching
    PenInventory row is what `store.services.purchase_skin` checks to block
    double-spends/duplicate purchases (see requirement #39)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_purchases")
    skin = models.ForeignKey("game.PenSkin", on_delete=models.CASCADE, related_name="purchases")
    price_paid_pp = models.PositiveIntegerField()
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user.username} bought {self.skin.name} for {self.price_paid_pp}PP"
