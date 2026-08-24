from django.contrib import admin

from .models import Match, MatchPlayer, MatchmakingTicket, PrivateRoom


class MatchPlayerInline(admin.TabularInline):
    model = MatchPlayer
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "match_type", "status", "arena", "winner", "created_at", "duration_seconds")
    list_filter = ("match_type", "status")
    inlines = [MatchPlayerInline]


@admin.register(PrivateRoom)
class PrivateRoomAdmin(admin.ModelAdmin):
    list_display = ("code", "host", "guest", "arena", "status", "created_at")
    list_filter = ("status",)


@admin.register(MatchmakingTicket)
class MatchmakingTicketAdmin(admin.ModelAdmin):
    list_display = ("user", "rating_at_time", "status", "room", "created_at")
    list_filter = ("status",)
