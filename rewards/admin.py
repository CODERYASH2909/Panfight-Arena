from django.contrib import admin

from .models import PenPointTransaction


@admin.register(PenPointTransaction)
class PenPointTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "balance_after", "created_at")
    list_filter = ("reason",)
    search_fields = ("user__username", "note")
    readonly_fields = ("balance_after",)
