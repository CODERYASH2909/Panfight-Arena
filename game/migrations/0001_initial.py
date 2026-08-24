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
            name="Pen",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=60)),
                ("description", models.CharField(max_length=200)),
                ("mass", models.FloatField(default=1.0)),
                ("max_power", models.FloatField(default=1.0)),
                ("friction", models.FloatField(default=1.0)),
                ("control", models.FloatField(default=1.0)),
                ("unlock_cost_pp", models.PositiveIntegerField(default=0)),
                ("icon", models.CharField(default="🖊️", max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name="PenSkin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60)),
                ("rarity", models.CharField(choices=[("common", "Common"), ("uncommon", "Uncommon"), ("rare", "Rare"), ("epic", "Epic"), ("legendary", "Legendary"), ("mythic", "Mythic")], default="common", max_length=12)),
                ("description", models.CharField(blank=True, default="", max_length=200)),
                ("body_color", models.CharField(default="#3b82f6", max_length=20)),
                ("accent_color", models.CharField(default="#93c5fd", max_length=20)),
                ("ink_color", models.CharField(default="#1d4ed8", max_length=20)),
                ("trail_color", models.CharField(default="#60a5fa", max_length=20)),
                ("glow", models.BooleanField(default=False)),
                ("pattern", models.CharField(blank=True, default="solid", max_length=30)),
                ("icon", models.CharField(default="🖊️", max_length=10)),
                ("price_pp", models.PositiveIntegerField(default=0)),
                ("is_starter", models.BooleanField(default=False)),
                ("is_purchasable", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["price_pp"]},
        ),
        migrations.CreateModel(
            name="Arena",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=60)),
                ("description", models.CharField(max_length=200)),
                ("bg_gradient_from", models.CharField(default="#0f172a", max_length=20)),
                ("bg_gradient_to", models.CharField(default="#1e293b", max_length=20)),
                ("bench_color", models.CharField(default="#8b5e3c", max_length=20)),
                ("accent_color", models.CharField(default="#38bdf8", max_length=20)),
                ("unlock_level", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["unlock_level"]},
        ),
        migrations.CreateModel(
            name="Achievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("description", models.CharField(max_length=200)),
                ("icon", models.CharField(default="🏆", max_length=10)),
                ("reward_pp", models.PositiveIntegerField(default=0)),
                ("reward_xp", models.PositiveIntegerField(default=0)),
                ("target_stat", models.CharField(help_text="Profile field name to compare, e.g. 'wins'", max_length=30)),
                ("target_value", models.PositiveIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name="PenInventory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("acquired_at", models.DateTimeField(auto_now_add=True)),
                ("skin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="owners", to="game.penskin")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="owned_skins", to="auth.user")),
            ],
        ),
        migrations.CreateModel(
            name="UserAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unlocked_at", models.DateTimeField(auto_now_add=True)),
                ("achievement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="unlocked_by", to="game.achievement")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="achievements", to="auth.user")),
            ],
            options={"ordering": ["-unlocked_at"]},
        ),
        migrations.AddConstraint(
            model_name="peninventory",
            constraint=models.UniqueConstraint(fields=("user", "skin"), name="unique_owned_skin"),
        ),
        migrations.AddConstraint(
            model_name="userachievement",
            constraint=models.UniqueConstraint(fields=("user", "achievement"), name="unique_user_achievement"),
        ),
    ]
