"""Game-side service helpers. Reward math itself lives in rewards.services —
this module only wires up starter-kit ownership, which is game-domain data
(Pen/PenSkin), not a Pen Points transaction."""

from .models import Pen, PenInventory, PenSkin


def grant_starter_kit(user):
    """Called once when a new User is created (see accounts.signals).
    Equips the Classic Ball Pen + Classic Blue skin so a brand-new player can
    jump straight into a battle with zero setup."""
    profile = user.profile

    starter_pen = Pen.objects.filter(kind=Pen.Kind.CLASSIC).first()
    starter_skin = PenSkin.objects.filter(is_starter=True).first()

    if starter_skin:
        PenInventory.objects.get_or_create(user=user, skin=starter_skin)
        profile.equipped_skin = starter_skin

    if starter_pen:
        profile.equipped_pen = starter_pen

    from django.contrib.auth import get_user_model  # noqa
    from .models import Arena
    default_arena = Arena.objects.filter(slug=Arena.Slug.CLASSROOM).first()
    if default_arena:
        profile.favorite_arena = default_arena

    profile.save(update_fields=["equipped_pen", "equipped_skin", "favorite_arena"])
