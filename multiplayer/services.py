from django.db import transaction
from django.utils import timezone

from accounts.models import Notification
from game.models import Arena
from rewards.services import apply_match_result_rewards, check_achievements

from .models import Match, MatchPlayer, MatchmakingTicket, PrivateRoom

RATING_RANGE = 400  # how far apart two players' ratings can be and still match


@transaction.atomic
def try_pair_quick_match(ticket: MatchmakingTicket):
    """Looks for another SEARCHING ticket within RATING_RANGE, and if found,
    pairs them into a fresh PrivateRoom + Match. Called every time a ticket
    is created or polled, so pairing happens within one poll cycle of both
    players being in the queue."""
    if ticket.status != MatchmakingTicket.Status.SEARCHING:
        return ticket.room

    candidates = (
        MatchmakingTicket.objects.select_for_update()
        .filter(status=MatchmakingTicket.Status.SEARCHING)
        .exclude(user=ticket.user)
        .exclude(id=ticket.id)
    )
    for other in candidates:
        if abs(other.rating_at_time - ticket.rating_at_time) <= RATING_RANGE:
            arena = Arena.objects.filter(is_active=True).order_by("?").first()
            match = Match.objects.create(match_type=Match.MatchType.QUICK, arena=arena, status=Match.Status.PENDING)
            room = PrivateRoom.objects.create(
                host=other.user, guest=ticket.user, arena=arena,
                status=PrivateRoom.Status.READY, match=match,
            )
            ticket.status = MatchmakingTicket.Status.MATCHED
            ticket.room = room
            ticket.save(update_fields=["status", "room"])
            other.status = MatchmakingTicket.Status.MATCHED
            other.room = room
            other.save(update_fields=["status", "room"])
            return room
    return None


@transaction.atomic
def finish_online_match(match: Match, winner_user, loser_user, winner_pen=None, winner_skin=None,
                         loser_pen=None, loser_skin=None):
    """The single server-authoritative place an *online* PenFight match gets
    scored. Called from the WebSocket consumer once it has decided a winner
    (i.e. one side reported their pen fell off the bench). Never trust a
    client-submitted winner directly — this function is the only path that
    writes Match.finish() + grants rewards for online play."""
    match.finish(winner_user)
    match.started_at = match.started_at or match.created_at
    match.save(update_fields=["started_at"])

    MatchPlayer.objects.update_or_create(
        match=match, slot="player1",
        defaults=dict(user=winner_user, pen=winner_pen, skin=winner_skin, is_winner=True),
    )
    MatchPlayer.objects.update_or_create(
        match=match, slot="player2",
        defaults=dict(user=loser_user, pen=loser_pen, skin=loser_skin, is_winner=False),
    )

    winner_profile = winner_user.profile
    winner_profile.register_match_result(won=True, knockout=True)
    loser_user.profile.register_match_result(won=False)

    winner_rewards = apply_match_result_rewards(winner_user, True, win_streak=winner_profile.current_win_streak)
    loser_rewards = apply_match_result_rewards(loser_user, False)

    winner_achievements = check_achievements(winner_user)
    check_achievements(loser_user)

    Notification.objects.create(
        user=winner_user, notif_type="match_result",
        message=f"You defeated {loser_user.username} in PenFight Arena!",
    )
    Notification.objects.create(
        user=loser_user, notif_type="match_result",
        message=f"{winner_user.username} knocked your pen off the bench. Rematch?",
    )

    return {
        "winner_rewards": winner_rewards,
        "loser_rewards": loser_rewards,
        "winner_achievements": [{"name": a.name, "icon": a.icon} for a in winner_achievements],
    }
