import django.conf
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PenPointTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.IntegerField(help_text="Positive = earned, negative = spent")),
                ("reason", models.CharField(choices=[("match_win", "Match Win"), ("match_loss", "Match Loss"), ("win_streak", "Win Streak Bonus"), ("daily", "Daily Activity"), ("achievement", "Achievement"), ("tournament", "Tournament"), ("store_purchase", "Store Purchase"), ("admin_grant", "Admin Grant"), ("starter", "Starter Grant")], max_length=20)),
                ("balance_after", models.PositiveIntegerField()),
                ("note", models.CharField(blank=True, default="", max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pp_transactions", to="auth.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
