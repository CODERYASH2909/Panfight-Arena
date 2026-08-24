import django.conf
import django.db.models.deletion
import multiplayer.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
        ("game", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Match",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("match_type", models.CharField(choices=[("local", "Local Battle"), ("private", "Private Room"), ("quick", "Quick Match"), ("friend", "Friend Challenge")], max_length=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("in_progress", "In Progress"), ("finished", "Finished"), ("abandoned", "Abandoned")], default="pending", max_length=15)),
                ("room_code", models.CharField(blank=True, default="", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("arena", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="matches", to="game.arena")),
                ("winner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="auth.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PrivateRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(default=multiplayer.models.generate_room_code, max_length=10, unique=True)),
                ("status", models.CharField(choices=[("waiting", "Waiting for opponent"), ("ready", "Both players ready"), ("in_progress", "In progress"), ("finished", "Finished")], default="waiting", max_length=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("arena", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.arena")),
                ("guest", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="joined_rooms", to="auth.user")),
                ("host", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hosted_rooms", to="auth.user")),
                ("match", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="room", to="multiplayer.match")),
            ],
        ),
        migrations.CreateModel(
            name="MatchPlayer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_name", models.CharField(blank=True, default="", max_length=40)),
                ("slot", models.CharField(choices=[("player1", "Player 1"), ("player2", "Player 2")], max_length=10)),
                ("is_winner", models.BooleanField(default=False)),
                ("match", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="players", to="multiplayer.match")),
                ("pen", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.pen")),
                ("skin", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.penskin")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="match_history", to="auth.user")),
            ],
        ),
        migrations.CreateModel(
            name="MatchmakingTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating_at_time", models.IntegerField(default=0)),
                ("status", models.CharField(choices=[("searching", "Searching"), ("matched", "Matched"), ("cancelled", "Cancelled")], default="searching", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("room", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="multiplayer.privateroom")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matchmaking_tickets", to="auth.user")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="matchplayer",
            constraint=models.UniqueConstraint(fields=("match", "slot"), name="unique_match_slot"),
        ),
    ]
