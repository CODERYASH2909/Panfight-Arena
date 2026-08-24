from django.contrib import admin

from .models import Achievement, Arena, Pen, PenInventory, PenSkin, UserAchievement


@admin.register(Pen)
class PenAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "mass", "max_power", "friction", "control", "unlock_cost_pp")


@admin.register(PenSkin)
class PenSkinAdmin(admin.ModelAdmin):
    list_display = ("name", "rarity", "price_pp", "is_starter", "is_purchasable", "is_featured")
    list_filter = ("rarity", "is_purchasable", "is_featured")
    list_editable = ("price_pp", "is_purchasable", "is_featured")
    search_fields = ("name",)


@admin.register(PenInventory)
class PenInventoryAdmin(admin.ModelAdmin):
    list_display = ("user", "skin", "acquired_at")
    search_fields = ("user__username", "skin__name")


@admin.register(Arena)
class ArenaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "unlock_level", "is_active")
    list_editable = ("is_active",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "target_stat", "target_value", "reward_pp", "reward_xp")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "unlocked_at")
