from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from game.models import PenInventory, PenSkin
from .services import purchase_skin


@login_required
def store_home(request):
    owned_ids = set(PenInventory.objects.filter(user=request.user).values_list("skin_id", flat=True))
    featured = PenSkin.objects.filter(is_featured=True, is_purchasable=True)
    all_skins = PenSkin.objects.filter(is_purchasable=True)
    return render(request, "store/store.html", {
        "featured": featured,
        "all_skins": all_skins,
        "owned_ids": owned_ids,
    })


@login_required
@require_POST
def buy_skin(request, skin_id):
    skin = get_object_or_404(PenSkin, id=skin_id)
    result = purchase_skin(request.user, skin)
    if result.success:
        messages.success(request, f"Purchased {skin.name}!")
    else:
        messages.error(request, result.error)
    return redirect("store:home")
