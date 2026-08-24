from django.contrib import admin

from .models import FriendRequest, Friendship, Notification, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "xp", "pen_points", "rating", "rank_tier", "wins", "losses", "win_rate")
    list_filter = ("rank_tier",)
    search_fields = ("user__username",)
    readonly_fields = ("win_rate",)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("user_a", "user_b", "created_at")


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_filter = ("status",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notif_type", "message", "is_read", "created_at")
    list_filter = ("notif_type", "is_read")
