from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Every new user automatically gets a PenFight Arena profile with a
    starter pen + skin equipped, handled in game.services.grant_starter_kit
    to avoid circular-import issues (game app depends on nothing here)."""
    if created:
        Profile.objects.get_or_create(user=instance)
        from game.services import grant_starter_kit
        grant_starter_kit(instance)
