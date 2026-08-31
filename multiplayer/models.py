import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_room_code():
    chars = string.ascii_uppercase + string.digits
    return "PF-" + "".join(random.choices(chars, k=4))


class Match(models.Model):
    class MatchType(models.TextChoices):
        LOCAL = "local", "Local Battle"
        PRIVATE = "private", "Private Room"
        QUICK = "quick", "Quick Match"
        FRIEND = "friend", "Friend Challenge"
        TEAM_2V2 = "team_2v2", "2v2 Team Battle"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"

    match_type = models.CharField(max_length=12, choices=MatchType.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    arena = models.ForeignKey("game.Arena", on_delete=models.SET_NULL, null=True, related_name="matches")
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    room_code = models.CharField(max_length=10, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Match #{self.id} ({self.get_match_type_display()})"

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    def finish(self, winner_user):
        self.status = Match.Status.FINISHED
        self.winner = winner_user
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "winner", "finished_at"])


class MatchPlayer(models.Model):
    SLOT_CHOICES = [
        ("player1", "Player 1"),
        ("player2", "Player 2"),
        ("t1p1", "Team 1 Player 1"),
        ("t1p2", "Team 1 Player 2"),
        ("t2p1", "Team 2 Player 1"),
        ("t2p2", "Team 2 Player 2"),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_history"
    )
    guest_name = models.CharField(max_length=40, blank=True, default="")  # for local Player 2 w/o account
    slot = models.CharField(max_length=10, choices=SLOT_CHOICES)
    pen = models.ForeignKey("game.Pen", on_delete=models.SET_NULL, null=True, related_name="+")
    skin = models.ForeignKey("game.PenSkin", on_delete=models.SET_NULL, null=True, related_name="+")
    is_winner = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["match", "slot"], name="unique_match_slot")]

    @property
    def display_name(self):
        return self.user.username if self.user else (self.guest_name or "Guest")


class PrivateRoom(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for players"
        FILLING = "filling", "Filling slots"  # 2v2: some but not all players joined
        READY = "ready", "All players ready"
        IN_PROGRESS = "in_progress", "In progress"
        FINISHED = "finished", "Finished"

    class RoomType(models.TextChoices):
        ONE_V_ONE = "1v1", "1v1"
        TWO_V_TWO = "2v2", "2v2 Team Battle"

    code = models.CharField(max_length=10, unique=True, default=generate_room_code)
    room_type = models.CharField(max_length=3, choices=RoomType.choices, default=RoomType.ONE_V_ONE)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_rooms")
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms"
    )
    # Extra slots for 2v2 team battles
    team1_player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="team1_rooms"
    )
    team2_player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="team2_rooms"
    )
    arena = models.ForeignKey("game.Arena", on_delete=models.SET_NULL, null=True, related_name="+")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.WAITING)
    match = models.OneToOneField(Match, null=True, blank=True, on_delete=models.SET_NULL, related_name="room")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def max_players(self):
        return 4 if self.room_type == self.RoomType.TWO_V_TWO else 2

    @property
    def is_full(self):
        if self.room_type == self.RoomType.TWO_V_TWO:
            return all([self.host_id, self.guest_id, self.team1_player2_id, self.team2_player2_id])
        return bool(self.host_id and self.guest_id)

    @property
    def all_players(self):
        """Returns a list of all non-None player users."""
        players = [self.host]
        if self.guest:
            players.append(self.guest)
        if self.team1_player2:
            players.append(self.team1_player2)
        if self.team2_player2:
            players.append(self.team2_player2)
        return players

    @property
    def player_count(self):
        return len(self.all_players)

    def slot_for_user(self, user):
        """Returns the slot name for a given user in a 2v2 room."""
        if user.id == self.host_id:
            return "t1p1"
        if user.id == self.team1_player2_id:
            return "t1p2"
        if user.id == self.guest_id:
            return "t2p1"
        if user.id == self.team2_player2_id:
            return "t2p2"
        return None


class MatchmakingTicket(models.Model):
    class Status(models.TextChoices):
        SEARCHING = "searching", "Searching"
        MATCHED = "matched", "Matched"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matchmaking_tickets")
    rating_at_time = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SEARCHING)
    room = models.ForeignKey(PrivateRoom, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
