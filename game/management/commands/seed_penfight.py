from django.core.management.base import BaseCommand

from game.models import Achievement, Arena, Pen, PenSkin


class Command(BaseCommand):
    help = "Seeds PenFight Arena with pens, skins, arenas, and achievements."

    def handle(self, *args, **options):
        self._seed_pens()
        self._seed_skins()
        self._seed_arenas()
        self._seed_achievements()
        self.stdout.write(self.style.SUCCESS("PenFight Arena seed data loaded."))

    def _seed_pens(self):
        pens = [
            dict(kind="classic", name="Classic Ball Pen", description="Balanced in every way. The pen every fight starts with.",
                 mass=1.0, max_power=1.0, friction=1.0, control=1.0, unlock_cost_pp=0, icon="🖊️"),
            dict(kind="heavy", name="Heavy Pen", description="More mass, harder knockback — but slower to move.",
                 mass=1.3, max_power=1.15, friction=1.15, control=0.9, unlock_cost_pp=1500, icon="🖋️"),
            dict(kind="speed", name="Speed Pen", description="Fast and slippery, but a little harder to control.",
                 mass=0.8, max_power=0.95, friction=0.8, control=0.9, unlock_cost_pp=1500, icon="✒️"),
            dict(kind="precision", name="Precision Pen", description="Tighter aim cone, more predictable flicks.",
                 mass=0.95, max_power=0.95, friction=1.0, control=1.2, unlock_cost_pp=2000, icon="🖊️"),
            dict(kind="balanced", name="Balanced Pen", description="A gentle all-rounder for players who like consistency.",
                 mass=1.0, max_power=1.0, friction=0.95, control=1.05, unlock_cost_pp=1000, icon="🖊️"),
        ]
        for p in pens:
            Pen.objects.update_or_create(kind=p["kind"], defaults=p)
        self.stdout.write("  Pens seeded.")

    def _seed_skins(self):
        skins = [
            dict(name="Classic Blue", rarity="common", price_pp=0, is_starter=True, is_purchasable=False,
                 body_color="#3b82f6", accent_color="#93c5fd", ink_color="#1d4ed8", trail_color="#60a5fa", icon="🔵"),
            dict(name="Forest Green", rarity="common", price_pp=500,
                 body_color="#16a34a", accent_color="#86efac", ink_color="#166534", trail_color="#4ade80", icon="🟢"),
            dict(name="Sunset Orange", rarity="uncommon", price_pp=1200,
                 body_color="#f97316", accent_color="#fed7aa", ink_color="#c2410c", trail_color="#fb923c", icon="🟠",
                 pattern="stripes"),
            dict(name="Ice Pen", rarity="rare", price_pp=2500,
                 body_color="#0ea5e9", accent_color="#e0f2fe", ink_color="#0369a1", trail_color="#7dd3fc", icon="❄️",
                 pattern="crystal", glow=True),
            dict(name="Fire Pen", rarity="rare", price_pp=2500,
                 body_color="#ef4444", accent_color="#fecaca", ink_color="#991b1b", trail_color="#f87171", icon="🔥",
                 pattern="flame", glow=True, is_featured=True),
            dict(name="Lightning Pen", rarity="epic", price_pp=4000,
                 body_color="#eab308", accent_color="#fef9c3", ink_color="#854d0e", trail_color="#facc15", icon="⚡",
                 pattern="bolt", glow=True, is_featured=True),
            dict(name="Galaxy Pen", rarity="epic", price_pp=7500,
                 body_color="#7c3aed", accent_color="#ddd6fe", ink_color="#4c1d95", trail_color="#a78bfa", icon="🌌",
                 pattern="stars", glow=True, is_featured=True),
            dict(name="Cyber Pen", rarity="legendary", price_pp=9000,
                 body_color="#06b6d4", accent_color="#a5f3fc", ink_color="#155e75", trail_color="#22d3ee", icon="🤖",
                 pattern="circuit", glow=True),
            dict(name="Dragon Pen", rarity="legendary", price_pp=9500,
                 body_color="#b91c1c", accent_color="#fbbf24", ink_color="#7f1d1d", trail_color="#f59e0b", icon="🐉",
                 pattern="scales", glow=True),
            dict(name="Shadow Pen", rarity="mythic", price_pp=12000,
                 body_color="#18181b", accent_color="#71717a", ink_color="#09090b", trail_color="#a1a1aa", icon="💀",
                 pattern="smoke", glow=True),
            dict(name="Golden Pen", rarity="mythic", price_pp=10000,
                 body_color="#d4af37", accent_color="#fff8dc", ink_color="#92720c", trail_color="#f4d35e", icon="👑",
                 pattern="gold-leaf", glow=True),
        ]
        for s in skins:
            PenSkin.objects.update_or_create(name=s["name"], defaults=s)
        self.stdout.write("  Skins seeded.")

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
