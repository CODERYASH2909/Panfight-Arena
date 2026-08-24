import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Achievement, Arena, Pen, PenInventory, PenSkin, UserAchievement


def landing(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return render(request, "game/landing.html")


def how_it_works(request):
    return render(request, "game/how_it_works.html")


@login_required
def my_pen(request):
    profile = request.user.profile
    pens = Pen.objects.all()
    owned_skin_ids = set(PenInventory.objects.filter(user=request.user).values_list("skin_id", flat=True))
    skins = PenSkin.objects.all()

    if request.method == "POST":
        pen_id = request.POST.get("pen_id")
        skin_id = request.POST.get("skin_id")
        pen = get_object_or_404(Pen, id=pen_id)
        skin = get_object_or_404(PenSkin, id=skin_id)
        if skin.id not in owned_skin_ids:
            messages.error(request, "You don't own that skin yet — visit the Pen Store.")
            return redirect("game:my_pen")
        profile.equipped_pen = pen
        profile.equipped_skin = skin
        profile.save(update_fields=["equipped_pen", "equipped_skin"])
        messages.success(request, "Loadout saved.")
        return redirect("game:my_pen")

    return render(request, "game/my_pen.html", {
        "pens": pens,
        "skins": skins,
        "owned_skin_ids": owned_skin_ids,
        "profile": profile,
    })


@login_required
def collection(request):
    owned = PenInventory.objects.filter(user=request.user).select_related("skin")
    owned_ids = set(owned.values_list("skin_id", flat=True))
    all_skins = PenSkin.objects.all()
    return render(request, "game/collection.html", {
        "all_skins": all_skins,
        "owned_ids": owned_ids,
        "owned_count": len(owned_ids),
        "total_count": all_skins.count(),
    })


@login_required
def local_battle_setup(request):
    arenas = Arena.objects.filter(is_active=True)
    pens = Pen.objects.all()
    skins = PenSkin.objects.all()
    return render(request, "game/local_setup.html", {
        "arenas": arenas, "pens": pens, "skins": skins,
    })


@login_required
def local_battle_play(request):
    """Renders the canvas battle screen. Player/pen/skin/arena choices are
    passed via query string from the setup screen and read client-side —
    local battles are entirely client-authoritative since both players share
    one device (no rewards are at stake for the non-authenticated 'Player 2'
    slot)."""
    arena_slug = request.GET.get("arena", Arena.Slug.CLASSROOM)
    arena = get_object_or_404(Arena, slug=arena_slug)
    return render(request, "game/battle_local.html", {"arena": arena})


@login_required
@require_POST
def local_battle_result(request):
    """Local-battle games only reward the logged-in Player 1 slot, and only
    when Player 2 was a guest (no account to reward). This keeps rewards
    server-authoritative even for hotseat play: the client reports *who
    won*, but the server decides what that's worth."""
    from rewards.services import apply_match_result_rewards, check_achievements

    data = json.loads(request.body or "{}")
    winner_slot = data.get("winner")  # "player1" or "player2"
    won = winner_slot == "player1"

    profile = request.user.profile
    profile.register_match_result(won=won, knockout=True)
    reward_summary = apply_match_result_rewards(request.user, won, win_streak=profile.current_win_streak)
    newly_unlocked = check_achievements(request.user)

    return _json_ok({
        "rewards": reward_summary,
        "achievements": [{"name": a.name, "icon": a.icon} for a in newly_unlocked],
        "profile": {
            "level": profile.level, "xp": profile.xp, "xp_needed": profile.xp_to_next_level,
            "pen_points": profile.pen_points, "rank_tier": profile.rank_tier, "rating": profile.rating,
        },
    })


@login_required
def achievements_view(request):
    unlocked_ids = set(UserAchievement.objects.filter(user=request.user).values_list("achievement_id", flat=True))
    achievements = Achievement.objects.all()
    return render(request, "game/achievements.html", {
        "achievements": achievements, "unlocked_ids": unlocked_ids,
    })


def _json_ok(payload):
    from django.http import JsonResponse
    payload["ok"] = True
    return JsonResponse(payload)
