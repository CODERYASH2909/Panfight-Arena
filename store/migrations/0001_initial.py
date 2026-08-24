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
            name="StorePurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price_paid_pp", models.PositiveIntegerField()),
                ("purchased_at", models.DateTimeField(auto_now_add=True)),
                ("skin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchases", to="game.penskin")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="store_purchases", to="auth.user")),
            ],
            options={"ordering": ["-purchased_at"]},
        ),
    ]
