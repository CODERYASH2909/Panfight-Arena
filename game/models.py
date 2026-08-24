from django.conf import settings
from django.db import models


class Pen(models.Model):
    """A pen archetype/class. Stats are intentionally kept close together —
    see settings docs / design notes: PenFight Arena is cosmetics-first,
    gameplay stats vary only slightly between pen types so nothing is
    pay-to-win."""

    class Kind(models.TextChoices):
        CLASSIC = "classic", "Classic Ball Pen"
        HEAVY = "heavy", "Heavy Pen"
        SPEED = "speed", "Speed Pen"
        PRECISION = "precision", "Precision Pen"
        BALANCED = "balanced", "Balanced Pen"

    kind = models.CharField(max_length=20, choices=Kind.choices, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200)

    # Gameplay stats — small variance on purpose (fairness constraint).
    mass = models.FloatField(default=1.0)          # affects knockback dealt/received
    max_power = models.FloatField(default=1.0)     # multiplier on flick strength
    friction = models.FloatField(default=1.0)       # multiplier on how quickly it slows
    control = models.FloatField(default=1.0)         # affects aim assist / spread

    unlock_cost_pp = models.PositiveIntegerField(default=0)  # 0 = free/starter
    icon = models.CharField(max_length=10, default="🖊️")

    def __str__(self):
        return self.name


class PenSkin(models.Model):
    class Rarity(models.TextChoices):
        COMMON = "common", "Common"
        UNCOMMON = "uncommon", "Uncommon"
        RARE = "rare", "Rare"
        EPIC = "epic", "Epic"
        LEGENDARY = "legendary", "Legendary"
        MYTHIC = "mythic", "Mythic"

    name = models.CharField(max_length=60)
    rarity = models.CharField(max_length=12, choices=Rarity.choices, default=Rarity.COMMON)
    description = models.CharField(max_length=200, blank=True, default="")

    # Purely cosmetic rendering data consumed by the canvas engine.
    body_color = models.CharField(max_length=20, default="#3b82f6")
    accent_color = models.CharField(max_length=20, default="#93c5fd")
    ink_color = models.CharField(max_length=20, default="#1d4ed8")
    trail_color = models.CharField(max_length=20, default="#60a5fa")
    glow = models.BooleanField(default=False)
    pattern = models.CharField(max_length=30, blank=True, default="solid")
    icon = models.CharField(max_length=10, default="🖊️")

    price_pp = models.PositiveIntegerField(default=0)
    is_starter = models.BooleanField(default=False)
    is_purchasable = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price_pp"]

    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class PenInventory(models.Model):
    """Which skins a user owns."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_skins")
    skin = models.ForeignKey(PenSkin, on_delete=models.CASCADE, related_name="owners")
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "skin"], name="unique_owned_skin")]

    def __str__(self):
        return f"{self.user.username} owns {self.skin.name}"


class Arena(models.Model):
    class Slug(models.TextChoices):
        CLASSROOM = "classic-classroom", "Classic Classroom"
        COLLEGE = "college-classroom", "College Classroom"
        EXAM = "exam-room", "Exam Room"
        HOSTEL = "hostel-table", "Hostel Table"
        LAB = "computer-lab", "Computer Lab"
        CAFETERIA = "cafeteria-table", "Cafeteria Table"
        NEON = "neon-arena", "Neon Arena"

    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200)
    bg_gradient_from = models.CharField(max_length=20, default="#0f172a")
    bg_gradient_to = models.CharField(max_length=20, default="#1e293b")
    bench_color = models.CharField(max_length=20, default="#8b5e3c")
    accent_color = models.CharField(max_length=20, default="#38bdf8")
    unlock_level = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["unlock_level"]

    def __str__(self):
        return self.name


class Achievement(models.Model):
    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, default="🏆")
    reward_pp = models.PositiveIntegerField(default=0)
    reward_xp = models.PositiveIntegerField(default=0)
    # Machine-checkable target used by rewards.services.check_achievements
    target_stat = models.CharField(max_length=30, help_text="Profile field name to compare, e.g. 'wins'")
    target_value = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="unlocked_by")
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "achievement"], name="unique_user_achievement")]
        ordering = ["-unlocked_at"]
