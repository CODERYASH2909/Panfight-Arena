"""
Centralized reward logic for PenFight Arena.

Every place in the codebase that needs to hand out Pen Points, XP, or check
achievement progress calls into THIS module rather than re-implementing the
math. This is what requirement #28 in the design spec ("Do not duplicate
reward calculations throughout the project") is about, and it's also what
keeps online-match rewards server-authoritative: the client never computes
its own reward numbers, it only ever displays what the server returns.
"""
from django.conf import settings
from django.db import transaction

from accounts.models import Notification, Profile
from rewards.models import PenPointTransaction

REWARDS = settings.PENFIGHT_REWARDS


@transaction.atomic
def grant_pen_points(user, amount: int, reason: str, note: str = "") -> PenPointTransaction:
    """Atomically adjusts a user's Pen Points balance and writes a ledger row.
    `amount` may be negative (e.g. store purchases) — callers are responsible
    for checking sufficient balance beforehand via `has_enough_pp`."""
    profile = Profile.objects.select_for_update().get(user=user)
    profile.pen_points = max(0, profile.pen_points + amount)
    profile.save(update_fields=["pen_points"])
    return PenPointTransaction.objects.create(
        user=user, amount=amount, reason=reason, balance_after=profile.pen_points, note=note,
    )


def has_enough_pp(user, amount: int) -> bool:
    return user.profile.pen_points >= amount


@transaction.atomic
def grant_xp(user, amount: int):
    """Grants XP and returns a list of levels gained (empty if none), so
    callers can trigger a 'LEVEL UP!' animation client-side."""
    profile = Profile.objects.select_for_update().get(user=user)
    levels_gained = profile.add_xp(amount)
    for lvl in levels_gained:
        Notification.objects.create(
            user=user, notif_type="level_up", message=f"LEVEL UP! You reached Level {lvl}.",
        )
    return levels_gained


def apply_match_result_rewards(user, won: bool, win_streak: int = 0):
    """The single source of truth for what a finished match pays out.
    Returns a dict summarizing the rewards for the battle-end UI."""
    pp = REWARDS["MATCH_WIN_PP"] if won else REWARDS["MATCH_LOSS_PP"]
    xp = REWARDS["MATCH_WIN_XP"] if won else REWARDS["MATCH_LOSS_XP"]
    reason = PenPointTransaction.Reason.MATCH_WIN if won else PenPointTransaction.Reason.MATCH_LOSS

    grant_pen_points(user, pp, reason, note="PenFight match reward")
    streak_bonus = 0
    if won and win_streak >= REWARDS["WIN_STREAK_THRESHOLD"]:
        streak_bonus = REWARDS["WIN_STREAK_BONUS_PP"]
        grant_pen_points(user, streak_bonus, PenPointTransaction.Reason.WIN_STREAK, note=f"{win_streak}-win streak")

    levels_gained = grant_xp(user, xp)

    if won:
        Notification.objects.create(
            user=user, notif_type="match_result", message=f"Victory! +{pp}PP  +{xp}XP",
        )
    else:
        Notification.objects.create(
            user=user, notif_type="match_result", message=f"Defeat. +{pp}PP  +{xp}XP — rematch?",
        )

    return {"pp": pp, "xp": xp, "streak_bonus": streak_bonus, "levels_gained": levels_gained}


def grant_daily_reward_if_eligible(user):
    from django.utils import timezone
    profile = user.profile
    today = timezone.localdate()
    if profile.last_daily_reward_at == today:
        return None
    profile.last_daily_reward_at = today
    profile.save(update_fields=["last_daily_reward_at"])
    grant_pen_points(user, REWARDS["DAILY_LOGIN_PP"], PenPointTransaction.Reason.DAILY, note="Daily login")
    return REWARDS["DAILY_LOGIN_PP"]


def check_achievements(user):
    """Compares the user's Profile stats against every Achievement's target
    and unlocks + rewards any newly-earned ones. Returns newly unlocked
    Achievement objects for the UI to celebrate."""
    from game.models import Achievement, UserAchievement

    profile = user.profile
    already_unlocked_ids = set(
        UserAchievement.objects.filter(user=user).values_list("achievement_id", flat=True)
    )
    newly_unlocked = []
    for ach in Achievement.objects.exclude(id__in=already_unlocked_ids):
        current_value = getattr(profile, ach.target_stat, None)
        if current_value is None:
            continue
        if current_value >= ach.target_value:
            UserAchievement.objects.create(user=user, achievement=ach)
            if ach.reward_pp:
                grant_pen_points(user, ach.reward_pp, PenPointTransaction.Reason.ACHIEVEMENT, note=ach.name)
            if ach.reward_xp:
                grant_xp(user, ach.reward_xp)
            Notification.objects.create(
                user=user, notif_type="achievement",
                message=f"Achievement unlocked: {ach.icon} {ach.name}!",
            )
            newly_unlocked.append(ach)
    return newly_unlocked
