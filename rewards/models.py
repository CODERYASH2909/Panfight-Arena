from django.conf import settings
from django.db import models


class PenPointTransaction(models.Model):
    """Immutable ledger of every Pen Points change. Never mutate a user's
    balance directly elsewhere — always go through rewards.services so the
    ledger and the cached Profile.pen_points balance can't drift apart."""

    class Reason(models.TextChoices):
        MATCH_WIN = "match_win", "Match Win"
        MATCH_LOSS = "match_loss", "Match Loss"
        WIN_STREAK = "win_streak", "Win Streak Bonus"
        DAILY = "daily", "Daily Activity"
        ACHIEVEMENT = "achievement", "Achievement"
        TOURNAMENT = "tournament", "Tournament"
        STORE_PURCHASE = "store_purchase", "Store Purchase"
        ADMIN_GRANT = "admin_grant", "Admin Grant"
        STARTER = "starter", "Starter Grant"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pp_transactions")
    amount = models.IntegerField(help_text="Positive = earned, negative = spent")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    balance_after = models.PositiveIntegerField()
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.user.username}: {sign}{self.amount}PP ({self.reason})"
