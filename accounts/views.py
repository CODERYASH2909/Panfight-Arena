from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from game.models import Achievement, UserAchievement
from multiplayer.models import Match, MatchPlayer
from .forms import ProfileEditForm, SignUpForm
from .models import FriendRequest, Friendship, Notification, Profile


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to PenFight Arena, {user.username}! Your first pen awaits.")
            return redirect("accounts:dashboard")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    profile = request.user.profile
    recent_matches = (
        MatchPlayer.objects.filter(user=request.user)
        .select_related("match", "match__arena", "pen", "skin")
        .order_by("-match__created_at")[:5]
    )
    friends = Friendship.friends_of(request.user)[:6]
    incoming_requests = FriendRequest.objects.filter(to_user=request.user, status="pending")
    achievements_unlocked = UserAchievement.objects.filter(user=request.user).count()
    achievements_total = Achievement.objects.count()

    return render(request, "accounts/dashboard.html", {
        "profile": profile,
        "recent_matches": recent_matches,
        "friends": friends,
        "incoming_requests": incoming_requests,
        "achievements_unlocked": achievements_unlocked,
        "achievements_total": achievements_total,
    })


def profile_detail(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    matches = (
        MatchPlayer.objects.filter(user=user)
        .select_related("match", "match__arena")
        .order_by("-match__created_at")[:15]
    )
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
    is_self = request.user == user
    is_friend = request.user.is_authenticated and Friendship.are_friends(request.user, user)
    return render(request, "accounts/profile.html", {
        "profile_user": user,
        "profile": profile,
        "matches": matches,
        "achievements": achievements,
        "is_self": is_self,
        "is_friend": is_friend,
    })


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile", username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def leaderboard(request):
    tab = request.GET.get("tab", "global")
    base_qs = Profile.objects.select_related("user").order_by("-rating", "-wins")

    if tab == "friends":
        friend_ids = list(Friendship.friends_of(request.user).values_list("id", flat=True)) + [request.user.id]
        base_qs = base_qs.filter(user_id__in=friend_ids)
    # "weekly"/"monthly" tabs reuse the same all-time ranking table for now —
    # a season-scoped rating snapshot is a natural next step (see README).

    top_profiles = list(base_qs[:50])
    user_rank = None
    for idx, p in enumerate(top_profiles, start=1):
        if p.user_id == request.user.id:
            user_rank = idx
    return render(request, "accounts/leaderboard.html", {
        "profiles": top_profiles,
        "tab": tab,
        "user_rank": user_rank,
    })


@login_required
def friends_list(request):
    friends = Friendship.friends_of(request.user)
    incoming = FriendRequest.objects.filter(to_user=request.user, status="pending")
    outgoing = FriendRequest.objects.filter(from_user=request.user, status="pending")
    query = request.GET.get("q", "").strip()
    search_results = []
    if query:
        search_results = User.objects.filter(
            Q(username__icontains=query) & ~Q(id=request.user.id)
        ).exclude(id__in=friends.values_list("id", flat=True))[:12]
    return render(request, "accounts/friends.html", {
        "friends": friends,
        "incoming": incoming,
        "outgoing": outgoing,
        "query": query,
        "search_results": search_results,
    })


@login_required
@require_POST
def send_friend_request(request, username):
    to_user = get_object_or_404(User, username=username)
    if to_user == request.user:
        messages.error(request, "You can't friend yourself, champ.")
        return redirect("accounts:friends")
    if Friendship.are_friends(request.user, to_user):
        messages.info(request, "You're already friends.")
        return redirect("accounts:friends")
    FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user, status="pending")
    Notification.objects.create(
        user=to_user, notif_type="friend_request",
        message=f"{request.user.username} sent you a friend request!",
        link=f"/accounts/friends/",
    )
    messages.success(request, f"Friend request sent to {to_user.username}.")
    return redirect("accounts:friends")


@login_required
@require_POST
def respond_friend_request(request, request_id, action):
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user, status="pending")
    if action == "accept":
        fr.accept()
        messages.success(request, f"You're now friends with {fr.from_user.username}.")
    else:
        fr.decline()
        messages.info(request, "Friend request declined.")
    return redirect("accounts:friends")


@login_required
@require_POST
def remove_friend(request, username):
    other = get_object_or_404(User, username=username)
    a, b = sorted([request.user.id, other.id])
    Friendship.objects.filter(user_a_id=a, user_b_id=b).delete()
    messages.info(request, f"Removed {other.username} from your friends.")
    return redirect("accounts:friends")


@login_required
@require_POST
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return redirect(notif.link or "accounts:dashboard")


@login_required
@require_POST
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER", "accounts:dashboard"))
