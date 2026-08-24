from dataclasses import dataclass

from django.db import IntegrityError, transaction

from game.models import PenInventory, PenSkin
from rewards.models import PenPointTransaction
from rewards.services import grant_pen_points, has_enough_pp
from accounts.models import Notification
from .models import StorePurchase


@dataclass
class PurchaseResult:
    success: bool
    error: str = ""


@transaction.atomic
def purchase_skin(user, skin: PenSkin) -> PurchaseResult:
    if not skin.is_purchasable:
        return PurchaseResult(False, "This skin isn't available in the store right now.")

    if PenInventory.objects.filter(user=user, skin=skin).exists():
        return PurchaseResult(False, "You already own this skin.")

    if not has_enough_pp(user, skin.price_pp):
        return PurchaseResult(False, "Not enough Pen Points.")

    try:
        PenInventory.objects.create(user=user, skin=skin)
    except IntegrityError:
        # Race condition guard: unique constraint caught a duplicate purchase.
        return PurchaseResult(False, "You already own this skin.")

    grant_pen_points(
        user, -skin.price_pp, PenPointTransaction.Reason.STORE_PURCHASE, note=f"Purchased {skin.name}",
    )
    StorePurchase.objects.create(user=user, skin=skin, price_paid_pp=skin.price_pp)
    Notification.objects.create(
        user=user, notif_type="store_purchase", message=f"You unlocked {skin.icon} {skin.name}!",
    )
    return PurchaseResult(True)
