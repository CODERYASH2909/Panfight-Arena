import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Notification
from game.models import Arena
from .models import Match, MatchmakingTicket, PrivateRoom
from .services import try_pair_quick_match


@login_required
def private_room_create(request):
    if request.method == "POST":
        try:
            max_players = int(request.POST.get("max_players", 2))
        except (ValueError, TypeError):
            max_players = 2

        if max_players not in [2, 3, 4, 5]:
            messages.error(request, "Invalid room size. Supported values are 2, 3, 4, or 5 players.")
            return render(request, "multiplayer/room_create.html")

        arena = Arena.objects.filter(is_active=True).first()
        room = PrivateRoom.objects.create(
            host=request.user,
            arena=arena,
            max_players=max_players,
            status=PrivateRoom.Status.WAITING,
        )
        messages.success(request, f"Private battle room created ({max_players} Players)! Room Code: {room.code}")
        return redirect("multiplayer:room_lobby", code=room.code)

    return render(request, "multiplayer/room_create.html")


@login_required
def private_room_join(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        if not code:
            messages.error(request, "Please enter a valid room code.")
            return redirect("multiplayer:room_join")

        room = PrivateRoom.objects.filter(code__iexact=code).first()
        if not room:
            messages.error(request, "Room not found. Double-check the code and try again.")
            return redirect("multiplayer:room_join")

        if room.status in [PrivateRoom.Status.FINISHED, PrivateRoom.Status.CANCELLED]:
            messages.error(request, "Battle room is no longer available.")
            return redirect("multiplayer:room_join")

        if request.user in room.all_players:
            return redirect("multiplayer:room_lobby", code=room.code)

        if room.is_full or room.player_count >= room.max_players:
            messages.error(request, "Room is full.")
            return redirect("multiplayer:room_join")

        success = room.add_player(request.user)
        if not success:
            messages.error(request, "Room is full.")
            return redirect("multiplayer:room_join")

        messages.success(request, f"Joined battle room {room.code}!")
        return redirect("multiplayer:room_lobby", code=room.code)

    return render(request, "multiplayer/room_join.html")


@login_required
def room_lobby(request, code):
    room = PrivateRoom.objects.filter(code__iexact=code).first()
    if not room:
        messages.error(request, "Room not found.")
        return redirect("accounts:dashboard")

    if room.status == PrivateRoom.Status.CANCELLED:
        messages.error(request, "Battle room is no longer available.")
        return redirect("accounts:friends")

    if request.user not in room.all_players:
        if not room.is_full and room.status in [PrivateRoom.Status.WAITING, PrivateRoom.Status.READY]:
            joined = room.add_player(request.user)
            if not joined:
                messages.error(request, "Room is full.")
                return redirect("accounts:dashboard")
        else:
            messages.error(request, "You're not part of this battle room or room is full.")
            return redirect("accounts:dashboard")

    arenas = Arena.objects.filter(is_active=True)
    my_slot = room.slot_for_user(request.user)

    slots_info = []
    for i in range(1, room.max_players + 1):
        slot_key = f"player{i}"
        player_user = room.get_user_by_slot(slot_key)
        slots_info.append({
            "slot_key": slot_key,
            "slot_number": i,
            "user": player_user,
            "is_host": (player_user == room.host) if player_user else False,
            "is_me": (player_user == request.user) if player_user else False,
        })

    return render(request, "multiplayer/room_lobby.html", {
        "room": room,
        "arenas": arenas,
        "my_slot": my_slot,
        "slots_info": slots_info,
    })


@login_required
@require_POST
def room_set_arena(request, code):
    room = get_object_or_404(PrivateRoom, code__iexact=code, host=request.user)
    arena = get_object_or_404(Arena, id=request.POST.get("arena_id"))
    room.arena = arena
    room.save(update_fields=["arena"])
    return redirect("multiplayer:room_lobby", code=code)


@login_required
@require_POST
def room_start(request, code):
    room = get_object_or_404(PrivateRoom, code__iexact=code)
    if request.user != room.host:
        messages.error(request, "Only the host can start the match.")
        return redirect("multiplayer:room_lobby", code=code)

    if room.player_count < 2:
        messages.error(request, "Waiting for at least 1 more player to join before starting.")
        return redirect("multiplayer:room_lobby", code=code)

    if not room.match:
        match = Match.objects.create(
            match_type=Match.MatchType.PRIVATE,
            arena=room.arena,
            status=Match.Status.IN_PROGRESS,
            room_code=room.code,
        )
        room.match = match
    room.status = PrivateRoom.Status.IN_PROGRESS
    room.save(update_fields=["match", "status"])
    return redirect("multiplayer:online_battle", code=code)


@login_required
def room_status(request, code):
    room = PrivateRoom.objects.filter(code__iexact=code).first()
    if not room:
        return JsonResponse({"exists": False, "status": "not_found"}, status=404)

    players_data = []
    for i in range(1, room.max_players + 1):
        slot_key = f"player{i}"
        p = room.get_user_by_slot(slot_key)
        if p:
            players_data.append({
                "slot": slot_key,
                "username": p.username,
                "is_host": (p == room.host),
            })

    return JsonResponse({
        "exists": True,
        "status": room.status,
        "max_players": room.max_players,
        "current_players": room.player_count,
        "is_full": room.is_full,
        "players": players_data,
        "host": room.host.username,
    })


@login_required
def online_battle(request, code):
    room = get_object_or_404(PrivateRoom, code__iexact=code)
    if request.user not in room.all_players:
        messages.error(request, "You're not part of this battle room.")
        return redirect("accounts:dashboard")

    my_slot = room.slot_for_user(request.user)

    players_config = []
    colors = ["#3b82f6", "#ef4444", "#10b981", "#facc15", "#a855f7"]
    accents = ["#93c5fd", "#fca5a5", "#6ee7b7", "#fef08a", "#e9d5ff"]
    trails = ["#60a5fa", "#f87171", "#34d399", "#fde047", "#c084fc"]
    asset_keys = ["classic-blue", "sunset-blaze", "neon-matrix", "golden-dragon", "cyber-phantom"]

    for i in range(1, room.max_players + 1):
        slot_key = f"player{i}"
        user = room.get_user_by_slot(slot_key)
        if user:
            equipped_pen = getattr(user.profile, "equipped_pen", None)
            equipped_skin = getattr(user.profile, "equipped_skin", None)
            idx = (i - 1) % 5
            players_config.append({
                "slot": slot_key,
                "username": user.username,
                "is_me": (user == request.user),
                "is_host": (user == room.host),
                "pen": {
                    "mass": equipped_pen.mass if equipped_pen else 1.0,
                    "friction": equipped_pen.friction if equipped_pen else 1.0,
                    "power": equipped_pen.max_power if equipped_pen else 1.0,
                    "color": equipped_skin.body_color if (equipped_skin and equipped_skin.body_color) else colors[idx],
                    "accent": equipped_skin.accent_color if (equipped_skin and equipped_skin.accent_color) else accents[idx],
                    "trail": equipped_skin.trail_color if (equipped_skin and equipped_skin.trail_color) else trails[idx],
                    "glow": equipped_skin.glow if equipped_skin else False,
                    "assetKey": equipped_skin.asset_key if (equipped_skin and equipped_skin.asset_key) else asset_keys[idx],
                    "penId": getattr(user.profile, "equipped_pen_id", None),
                    "skinId": getattr(user.profile, "equipped_skin_id", None),
                }
            })

    return render(request, "multiplayer/battle_online.html", {
        "room": room,
        "my_slot": my_slot,
        "players_config_json": json.dumps(players_config),
    })


# --- Quick match ------------------------------------------------------

@login_required
def quick_match_search(request):
    return render(request, "multiplayer/quick_match.html")


@login_required
@require_POST
def quick_match_start(request):
    ticket, _ = MatchmakingTicket.objects.get_or_create(
        user=request.user, status=MatchmakingTicket.Status.SEARCHING,
        defaults={"rating_at_time": request.user.profile.rating},
    )
    room = try_pair_quick_match(ticket)
    if room:
        return JsonResponse({"matched": True, "room_code": room.code})
    return JsonResponse({"matched": False})


@login_required
def quick_match_poll(request):
    ticket = MatchmakingTicket.objects.filter(
        user=request.user, status__in=[MatchmakingTicket.Status.SEARCHING, MatchmakingTicket.Status.MATCHED]
    ).order_by("-created_at").first()
    if not ticket:
        return JsonResponse({"matched": False, "searching": False})
    room = try_pair_quick_match(ticket) or ticket.room
    if room:
        if room.status == PrivateRoom.Status.READY and not room.match:
            match = Match.objects.create(
                match_type=Match.MatchType.QUICK, arena=room.arena,
                status=Match.Status.IN_PROGRESS, room_code=room.code,
            )
            room.match = match
            room.status = PrivateRoom.Status.IN_PROGRESS
            room.save(update_fields=["match", "status"])
        return JsonResponse({"matched": True, "room_code": room.code})
    return JsonResponse({"matched": False, "searching": True})


@login_required
@require_POST
def quick_match_cancel(request):
    MatchmakingTicket.objects.filter(user=request.user, status=MatchmakingTicket.Status.SEARCHING).update(
        status=MatchmakingTicket.Status.CANCELLED
    )
    return JsonResponse({"ok": True})


# --- Friend challenges --------------------------------------------------

@login_required
@require_POST
def challenge_friend(request, username):
    friend = get_object_or_404(User, username=username)
    if friend == request.user:
        messages.error(request, "You can't challenge yourself, champ.")
        return redirect("accounts:friends")

    arena = Arena.objects.filter(is_active=True).first()
    room = PrivateRoom.objects.create(
        host=request.user,
        guest=friend,
        arena=arena,
        max_players=2,
        status=PrivateRoom.Status.WAITING
    )
    Notification.objects.create(
        user=friend,
        notif_type="challenge",
        message=f"{request.user.username} challenged you to a PenFight!",
        link=f"/arena/room/{room.code}/accept/",
    )
    messages.success(request, f"Challenge sent to {friend.username}! Room code: {room.code}")
    return redirect("multiplayer:room_lobby", code=room.code)


@login_required
def accept_challenge(request, code):
    room = PrivateRoom.objects.filter(code__iexact=code).first()
    if not room or room.status in [PrivateRoom.Status.FINISHED, PrivateRoom.Status.CANCELLED]:
        messages.error(request, "Battle room is no longer available.")
        return redirect("accounts:friends")

    if room.guest and room.guest != request.user and room.host != request.user:
        messages.error(request, "Room is already full.")
        return redirect("accounts:friends")

    if not room.guest or room.guest == request.user:
        room.guest = request.user
        room.status = PrivateRoom.Status.READY
        room.save(update_fields=["guest", "status"])

    Notification.objects.filter(user=request.user, notif_type="challenge", link__icontains=room.code).update(is_read=True)
    messages.success(request, f"Accepted challenge from {room.host.username}!")
    return redirect("multiplayer:room_lobby", code=room.code)


@login_required
def decline_challenge(request, code):
    room = PrivateRoom.objects.filter(code__iexact=code).first()
    if room and room.status == PrivateRoom.Status.WAITING:
        room.status = PrivateRoom.Status.CANCELLED
        room.save(update_fields=["status"])

    Notification.objects.filter(user=request.user, notif_type="challenge", link__icontains=code).update(is_read=True)
    messages.info(request, "Challenge declined.")
    return redirect("accounts:friends")
