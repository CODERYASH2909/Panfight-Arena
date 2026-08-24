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

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"

    match_type = models.CharField(max_length=10, choices=MatchType.choices)
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
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_history"
    )
    guest_name = models.CharField(max_length=40, blank=True, default="")  # for local Player 2 w/o account
    slot = models.CharField(max_length=10, choices=[("player1", "Player 1"), ("player2", "Player 2")])
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
        WAITING = "waiting", "Waiting for opponent"
        READY = "ready", "Both players ready"
        IN_PROGRESS = "in_progress", "In progress"
        FINISHED = "finished", "Finished"

    code = models.CharField(max_length=10, unique=True, default=generate_room_code)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_rooms")
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="joined_rooms"
    )
    arena = models.ForeignKey("game.Arena", on_delete=models.SET_NULL, null=True, related_name="+")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.WAITING)
    match = models.OneToOneField(Match, null=True, blank=True, on_delete=models.SET_NULL, related_name="room")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


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
