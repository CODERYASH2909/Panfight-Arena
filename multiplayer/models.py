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
        ("player3", "Player 3"),
        ("player4", "Player 4"),
        ("player5", "Player 5"),
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
        FILLING = "filling", "Filling slots"
        READY = "ready", "All players ready"
        IN_PROGRESS = "in_progress", "In progress"
        FINISHED = "finished", "Finished"
        CANCELLED = "cancelled", "Cancelled"

    class RoomType(models.TextChoices):
        ONE_V_ONE = "1v1", "1v1"
        TWO_V_TWO = "2v2", "2v2 Team Battle"

    code = models.CharField(max_length=10, unique=True, default=generate_room_code)
    room_type = models.CharField(max_length=3, choices=RoomType.choices, default=RoomType.ONE_V_ONE)
    max_players = models.IntegerField(default=2, null=True, blank=True)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_rooms")
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms"
    )
    player3 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms_p3"
    )
    player4 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms_p4"
    )
    player5 = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms_p5"
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

    def save(self, *args, **kwargs):
        if not self.max_players:
            self.max_players = 2
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.player_count}/{self.max_players or 2})"

    @property
    def is_full(self):
        if self.room_type == self.RoomType.TWO_V_TWO:
            return all([self.host_id, self.guest_id, self.team1_player2_id, self.team2_player2_id])
        return len(self.all_players) >= (self.max_players or 2)

    @property
    def all_players(self):
        """Returns a list of all non-None player users in join order."""
        players = []
        if self.host:
            players.append(self.host)
        if self.guest:
            players.append(self.guest)
        if self.player3:
            players.append(self.player3)
        if self.player4:
            players.append(self.player4)
        if self.player5:
            players.append(self.player5)
        if self.room_type == self.RoomType.TWO_V_TWO:
            if self.team1_player2 and self.team1_player2 not in players:
                players.append(self.team1_player2)
            if self.team2_player2 and self.team2_player2 not in players:
                players.append(self.team2_player2)
        return players

    @property
    def player_count(self):
        return len(self.all_players)

    def slot_for_user(self, user):
        """Returns the slot name for a given user."""
        if not user or not user.is_authenticated:
            return None
        if user.id == self.host_id:
            return "player1" if self.room_type != self.RoomType.TWO_V_TWO else "t1p1"
        if user.id == self.guest_id:
            return "player2" if self.room_type != self.RoomType.TWO_V_TWO else "t2p1"
        if user.id == self.player3_id:
            return "player3"
        if user.id == self.player4_id:
            return "player4"
        if user.id == self.player5_id:
            return "player5"
        if user.id == self.team1_player2_id:
            return "t1p2"
        if user.id == self.team2_player2_id:
            return "t2p2"
        return None

    def get_user_by_slot(self, slot):
        mapping = {
            "player1": self.host,
            "player2": self.guest,
            "player3": self.player3,
            "player4": self.player4,
            "player5": self.player5,
            "t1p1": self.host,
            "t2p1": self.guest,
            "t1p2": self.team1_player2,
            "t2p2": self.team2_player2,
        }
        return mapping.get(slot)

    def add_player(self, user):
        """Adds user to the first open slot if capacity allows."""
        if user in self.all_players:
            return True
        if len(self.all_players) >= self.max_players:
            return False
        if not self.guest_id:
            self.guest = user
        elif not self.player3_id and self.max_players >= 3:
            self.player3 = user
        elif not self.player4_id and self.max_players >= 4:
            self.player4 = user
        elif not self.player5_id and self.max_players >= 5:
            self.player5 = user
        else:
            return False
        if len(self.all_players) >= self.max_players:
            self.status = PrivateRoom.Status.READY
        self.save()
        return True


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
