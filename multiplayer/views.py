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
    arena = Arena.objects.filter(is_active=True).first()
    room = PrivateRoom.objects.create(host=request.user, arena=arena)
    return redirect("multiplayer:room_lobby", code=room.code)


@login_required
def private_room_join(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        room = PrivateRoom.objects.filter(code=code).first()
        if not room:
            messages.error(request, "Invalid room code. Double-check and try again.")
            return redirect("multiplayer:room_join")
        if room.status != PrivateRoom.Status.WAITING:
            messages.error(request, "That room is no longer accepting players.")
            return redirect("multiplayer:room_join")
        if room.host == request.user:
            messages.error(request, "You can't join your own room.")
            return redirect("multiplayer:room_join")
        room.guest = request.user
        room.status = PrivateRoom.Status.READY
        room.save(update_fields=["guest", "status"])
        return redirect("multiplayer:room_lobby", code=room.code)
    return render(request, "multiplayer/room_join.html")


@login_required
def room_lobby(request, code):
    room = get_object_or_404(PrivateRoom, code=code)
    if request.user not in [room.host, room.guest]:
        messages.error(request, "You're not part of this room.")
        return redirect("game:landing")
    arenas = Arena.objects.filter(is_active=True)
    return render(request, "multiplayer/room_lobby.html", {"room": room, "arenas": arenas})


@login_required
@require_POST
def room_set_arena(request, code):
    room = get_object_or_404(PrivateRoom, code=code, host=request.user)
    arena = get_object_or_404(Arena, id=request.POST.get("arena_id"))
    room.arena = arena
    room.save(update_fields=["arena"])
    return redirect("multiplayer:room_lobby", code=code)


@login_required
@require_POST
def room_start(request, code):
    room = get_object_or_404(PrivateRoom, code=code, host=request.user)
    if room.status != PrivateRoom.Status.READY:
        messages.error(request, "Waiting for an opponent to join.")
        return redirect("multiplayer:room_lobby", code=code)
    if not room.match:
        match = Match.objects.create(
            match_type=Match.MatchType.PRIVATE, arena=room.arena,
            status=Match.Status.IN_PROGRESS, room_code=room.code,
        )
        room.match = match
    room.status = PrivateRoom.Status.IN_PROGRESS
    room.save(update_fields=["match", "status"])
    return redirect("multiplayer:online_battle", code=code)


@login_required
def room_status(request, code):
    room = get_object_or_404(PrivateRoom, code=code)
    return JsonResponse({"status": room.status, "has_guest": bool(room.guest_id)})


@login_required
def online_battle(request, code):
    room = get_object_or_404(PrivateRoom, code=code)
    if request.user not in [room.host, room.guest]:
        messages.error(request, "You're not part of this room.")
        return redirect("game:landing")
    my_slot = "player1" if request.user == room.host else "player2"
    opponent = room.guest if my_slot == "player1" else room.host
    return render(request, "multiplayer/battle_online.html", {
        "room": room, "my_slot": my_slot, "opponent": opponent,
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
    arena = Arena.objects.filter(is_active=True).first()
    room = PrivateRoom.objects.create(host=request.user, guest=friend, arena=arena, status=PrivateRoom.Status.READY)
    Notification.objects.create(
        user=friend, notif_type="challenge",
        message=f"🔥 {request.user.username} challenged you to a PenFight!",
        link=f"/arena/room/{room.code}/",
    )
    messages.success(request, f"Challenge sent to {friend.username}!")
    return redirect("multiplayer:room_lobby", code=room.code)
