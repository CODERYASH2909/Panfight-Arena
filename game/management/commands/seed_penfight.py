from django.core.management.base import BaseCommand
from game.models import Achievement, Arena, Pen, PenSkin
from accounts.models import Profile


class Command(BaseCommand):
    help = "Seeds PenFight Arena with normal pen, inferno pen, arenas, and achievements."

    def handle(self, *args, **options):
        self._seed_pens()
        self._seed_skins()
        self._seed_arenas()
        self._seed_achievements()
        self._cleanup_user_equipped()
        self.stdout.write(self.style.SUCCESS("PenFight Arena seed data loaded. Only Normal Pen & Inferno Pen remain active."))

    def _seed_pens(self):
        pens = [
            dict(kind="classic", name="Classic Ball Pen", description="Balanced in every way. The standard pen every fight starts with.",
                 mass=1.0, max_power=1.0, friction=1.0, control=1.0, unlock_cost_pp=0, icon="🖊️"),
            dict(kind="heavy", name="Inferno Pen", description="Magma forged pen with high knockback power and flame aura.",
                 mass=1.2, max_power=1.15, friction=1.05, control=0.95, unlock_cost_pp=4500, icon="🔥"),
        ]
        kept_kinds = [p["kind"] for p in pens]
        # Remove all other pens
        Pen.objects.exclude(kind__in=kept_kinds).delete()

        for p in pens:
            Pen.objects.update_or_create(kind=p["kind"], defaults=p)
        self.stdout.write("  Pens seeded (Normal & Inferno).")

    def _seed_skins(self):
        skins = [
            dict(name="Classic Blue", rarity="common", price_pp=0, is_starter=True, is_purchasable=False,
                 body_color="#2563eb", accent_color="#93c5fd", ink_color="#1e40af", trail_color="#60a5fa", icon="🖊️",
                 asset_key="classic-blue", description="A realistic everyday blue ball pen. Reliable and balanced."),

            dict(name="Inferno", rarity="epic", price_pp=4500, glow=True, is_featured=True, is_purchasable=True,
                 body_color="#18181b", accent_color="#ef4444", ink_color="#7f1d1d", trail_color="#f87171", icon="🔥",
                 asset_key="inferno", description="Matte black metallic body with pulsing magma red energy channels."),
        ]
        kept_names = [s["name"] for s in skins]
        # Remove all other skins
        PenSkin.objects.exclude(name__in=kept_names).delete()

        for s in skins:
            PenSkin.objects.update_or_create(name=s["name"], defaults=s)
        self.stdout.write("  Skins seeded (Classic Blue & Inferno).")

    def _seed_arenas(self):
        arenas = [
            dict(slug="classic-classroom", name="Classic Classroom", unlock_level=1,
                 description="Where it all began — a wooden school bench.",
                 bg_gradient_from="#1c1410", bg_gradient_to="#3a2a1c", bench_color="#8b5e3c", accent_color="#f59e0b"),
            dict(slug="college-classroom", name="College Classroom", unlock_level=3,
                 description="Modern tiered desks and whiteboards.",
                 bg_gradient_from="#0f172a", bg_gradient_to="#1e293b", bench_color="#64748b", accent_color="#38bdf8"),
            dict(slug="exam-room", name="Exam Room", unlock_level=5,
                 description="Silent, tense, rows of solo desks.",
                 bg_gradient_from="#1a1025", bg_gradient_to="#2d1b40", bench_color="#94a3b8", accent_color="#e11d48"),
            dict(slug="hostel-table", name="Hostel Table", unlock_level=7,
                 description="A cluttered study table, mid all-nighter.",
                 bg_gradient_from="#1f1a0f", bg_gradient_to="#3d3418", bench_color="#a16207", accent_color="#fbbf24"),
            dict(slug="computer-lab", name="Computer Lab", unlock_level=9,
                 description="Rows of monitors and humming machines.",
                 bg_gradient_from="#0a1f1a", bg_gradient_to="#0f3d33", bench_color="#334155", accent_color="#2dd4bf"),
            dict(slug="cafeteria-table", name="Cafeteria Table", unlock_level=11,
                 description="Lunch trays cleared, fight time.",
                 bg_gradient_from="#1a1512", bg_gradient_to="#332318", bench_color="#b45309", accent_color="#fb923c"),
            dict(slug="neon-arena", name="Neon Arena", unlock_level=15,
                 description="A futuristic competitive coliseum for the best PenFighters.",
                 bg_gradient_from="#0a0118", bg_gradient_to="#1a0a2e", bench_color="#4c1d95", accent_color="#e879f9"),
        ]
        for a in arenas:
            Arena.objects.update_or_create(slug=a["slug"], defaults=a)
        self.stdout.write("  Arenas seeded.")

    def _seed_achievements(self):
        achievements = [
            dict(key="first-fight", name="First Fight", description="Complete your first PenFight.",
                 icon="⚔️", reward_pp=100, reward_xp=50, target_stat="matches_played", target_value=1),
            dict(key="first-victory", name="First Victory", description="Win your first match.",
                 icon="🏆", reward_pp=150, reward_xp=100, target_stat="wins", target_value=1),
            dict(key="pen-master", name="Pen Master", description="Win 50 matches.",
                 icon="🎖️", reward_pp=1000, reward_xp=800, target_stat="wins", target_value=50),
            dict(key="knockout-king", name="Knockout King", description="Knock 100 opponents off the bench.",
                 icon="💥", reward_pp=1200, reward_xp=900, target_stat="knockouts", target_value=100),
            dict(key="unstoppable", name="Unstoppable", description="Win 10 matches in a row.",
                 icon="🔥", reward_pp=500, reward_xp=400, target_stat="best_win_streak", target_value=10),
            dict(key="pen-legend", name="Pen Legend", description="Reach Grandmaster rank.",
                 icon="👑", reward_pp=2000, reward_xp=1500, target_stat="rating", target_value=3600),
        ]
        for a in achievements:
            Achievement.objects.update_or_create(key=a["key"], defaults=a)
        self.stdout.write("  Achievements seeded.")

    def _cleanup_user_equipped(self):
        default_pen = Pen.objects.filter(kind="classic").first()
        default_skin = PenSkin.objects.filter(name="Classic Blue").first()
        for p in Profile.objects.all():
            if not p.equipped_pen:
                p.equipped_pen = default_pen
            if not p.equipped_skin:
                p.equipped_skin = default_skin
            p.save(update_fields=["equipped_pen", "equipped_skin"])
