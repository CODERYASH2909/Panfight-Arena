import django.conf
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
        ("game", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/")),
                ("bio", models.CharField(blank=True, default="", max_length=140)),
                ("level", models.PositiveIntegerField(default=1)),
                ("xp", models.PositiveIntegerField(default=0)),
                ("pen_points", models.PositiveIntegerField(default=250)),
                ("rating", models.IntegerField(default=0)),
                ("rank_tier", models.CharField(choices=[("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold"), ("platinum", "Platinum"), ("diamond", "Diamond"), ("master", "Master"), ("grandmaster", "Grandmaster")], default="bronze", max_length=20)),
                ("matches_played", models.PositiveIntegerField(default=0)),
                ("wins", models.PositiveIntegerField(default=0)),
                ("losses", models.PositiveIntegerField(default=0)),
                ("current_win_streak", models.PositiveIntegerField(default=0)),
                ("best_win_streak", models.PositiveIntegerField(default=0)),
                ("knockouts", models.PositiveIntegerField(default=0)),
                ("is_online", models.BooleanField(default=False)),
                ("last_daily_reward_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("equipped_pen", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.pen")),
                ("equipped_skin", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.penskin")),
                ("favorite_arena", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="game.arena")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to="auth.user")),
            ],
            options={"ordering": ["-rating"]},
        ),
        migrations.CreateModel(
            name="Friendship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user_a", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="friendships_a", to="auth.user")),
                ("user_b", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="friendships_b", to="auth.user")),
            ],
        ),
        migrations.CreateModel(
            name="FriendRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("from_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_requests", to="auth.user")),
                ("to_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_requests", to="auth.user")),
            ],
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notif_type", models.CharField(choices=[("friend_request", "Friend Request"), ("friend_accepted", "Friend Accepted"), ("challenge", "Challenge"), ("challenge_accepted", "Challenge Accepted"), ("match_result", "Match Result"), ("achievement", "Achievement Unlocked"), ("level_up", "Level Up"), ("rank_up", "Rank Up"), ("store_purchase", "Store Purchase")], max_length=30)),
                ("message", models.CharField(max_length=255)),
                ("link", models.CharField(blank=True, default="", max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="auth.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="friendship",
            constraint=models.UniqueConstraint(fields=("user_a", "user_b"), name="unique_friend_pair"),
        ),
        migrations.AddConstraint(
            model_name="friendrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "pending")), fields=("from_user", "to_user"), name="unique_pending_friend_request"),
        ),
    ]
