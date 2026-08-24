from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


RANK_TIERS = [
    ("bronze", "Bronze"),
    ("silver", "Silver"),
    ("gold", "Gold"),
    ("platinum", "Platinum"),
    ("diamond", "Diamond"),
    ("master", "Master"),
    ("grandmaster", "Grandmaster"),
]

# Rating thresholds that map to each rank tier. Used by Profile.recalc_rank().
RANK_THRESHOLDS = [
    (0, "bronze"),
    (600, "silver"),
    (1200, "gold"),
    (1800, "platinum"),
    (2400, "diamond"),
    (3000, "master"),
    (3600, "grandmaster"),
]


def xp_required_for_level(level: int) -> int:
    """XP needed to go from `level` to `level + 1`. Gentle upward curve."""
    return 400 + (level - 1) * 120


class Profile(models.Model):
    """Extends the built-in User with all PenFight Arena game state."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.CharField(max_length=140, blank=True, default="")

    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)

    pen_points = models.PositiveIntegerField(default=250)  # small starter grant

    rating = models.IntegerField(default=0)
    rank_tier = models.CharField(max_length=20, choices=RANK_TIERS, default="bronze")

    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    current_win_streak = models.PositiveIntegerField(default=0)
    best_win_streak = models.PositiveIntegerField(default=0)
    knockouts = models.PositiveIntegerField(default=0)

    equipped_pen = models.ForeignKey(
        "game.Pen", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    equipped_skin = models.ForeignKey(
        "game.PenSkin", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    favorite_arena = models.ForeignKey(
        "game.Arena", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    is_online = models.BooleanField(default=False)
    last_daily_reward_at = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-rating"]

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return round((self.wins / total) * 100, 1)

    @property
    def xp_to_next_level(self) -> int:
        return xp_required_for_level(self.level)

    def add_xp(self, amount: int):
        """Adds XP and rolls over levels. Returns list of levels gained (for UI)."""
        levels_gained = []
        self.xp += amount
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            levels_gained.append(self.level)
        self.save(update_fields=["xp", "level"])
        return levels_gained

    def recalc_rank(self):
        tier = "bronze"
        for threshold, name in RANK_THRESHOLDS:
            if self.rating >= threshold:
                tier = name
        if tier != self.rank_tier:
            self.rank_tier = tier
        self.save(update_fields=["rank_tier"])

    def register_match_result(self, won: bool, knockout: bool = False):
        self.matches_played += 1
        if won:
            self.wins += 1
            self.current_win_streak += 1
            self.best_win_streak = max(self.best_win_streak, self.current_win_streak)
            self.rating += 25
        else:
            self.losses += 1
            self.current_win_streak = 0
            self.rating = max(0, self.rating - 15)
        if knockout:
            self.knockouts += 1
        self.save(update_fields=[
            "matches_played", "wins", "losses", "current_win_streak", "best_win_streak", "rating", "knockouts",
        ])
        self.recalc_rank()

    def get_absolute_url(self):
        return reverse("accounts:profile", args=[self.user.username])


class Friendship(models.Model):
    """A confirmed, symmetric friendship between two users (one row per pair)."""

    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_a")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_b")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="unique_friend_pair"),
        ]

    @staticmethod
    def are_friends(u1, u2) -> bool:
        return Friendship.objects.filter(
            models.Q(user_a=u1, user_b=u2) | models.Q(user_a=u2, user_b=u1)
        ).exists()

    @staticmethod
    def friends_of(user):
        """Returns a User queryset of everyone `user` is friends with."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        pairs = Friendship.objects.filter(models.Q(user_a=user) | models.Q(user_b=user))
        friend_ids = set()
        for f in pairs:
            friend_ids.add(f.user_b_id if f.user_a_id == user.id else f.user_a_id)
        return User.objects.filter(id__in=friend_ids)


class FriendRequest(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")]

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_requests")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                condition=models.Q(status="pending"),
                name="unique_pending_friend_request",
            )
        ]

    def accept(self):
        self.status = "accepted"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])
        a, b = sorted([self.from_user_id, self.to_user_id])
        Friendship.objects.get_or_create(user_a_id=a, user_b_id=b)
        Notification.objects.create(
            user=self.from_user,
            notif_type="friend_accepted",
            message=f"{self.to_user.username} accepted your friend request!",
        )

    def decline(self):
        self.status = "declined"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])


class Notification(models.Model):
    NOTIF_TYPES = [
        ("friend_request", "Friend Request"),
        ("friend_accepted", "Friend Accepted"),
        ("challenge", "Challenge"),
        ("challenge_accepted", "Challenge Accepted"),
        ("match_result", "Match Result"),
        ("achievement", "Achievement Unlocked"),
        ("level_up", "Level Up"),
        ("rank_up", "Rank Up"),
        ("store_purchase", "Store Purchase"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES)
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.notif_type}] {self.message}"
