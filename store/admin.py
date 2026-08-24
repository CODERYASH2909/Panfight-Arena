from django.contrib import admin

from .models import StorePurchase


@admin.register(StorePurchase)
class StorePurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "skin", "price_paid_pp", "purchased_at")
    search_fields = ("user__username", "skin__name")
