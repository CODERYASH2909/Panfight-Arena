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
                 body_color="#2563eb", accent_color="#93c5fd", ink_color="#1e40af", trail_color="#60a5fa", icon="🖊️",
                 asset_key="classic-blue", description="A realistic everyday blue ball pen. Reliable and balanced."),

            dict(name="Stealth", rarity="uncommon", price_pp=1000,
                 body_color="#1e293b", accent_color="#64748b", ink_color="#020617", trail_color="#475569", icon="🕶️",
                 asset_key="stealth", description="Tactical matte carbon fiber pen with low-profile anti-reflective clip."),

            dict(name="Forest Guardian", rarity="uncommon", price_pp=1200,
                 body_color="#14532d", accent_color="#86efac", ink_color="#166534", trail_color="#4ade80", icon="🌿",
                 asset_key="forest-guardian", description="Ancient forest weapon with leaf engravings and translucent jade grip."),

            dict(name="Sunset Blaze", rarity="rare", price_pp=2200, is_featured=True,
                 body_color="#ea580c", accent_color="#fef08a", ink_color="#9a3412", trail_color="#fb923c", icon="🌅",
                 asset_key="sunset-blaze", description="Fire and sunset themed ball pen with metallic gold tip and warm ember glow."),

            dict(name="Frostbite", rarity="rare", price_pp=2500, glow=True,
                 body_color="#0284c7", accent_color="#e0f2fe", ink_color="#075985", trail_color="#7dd3fc", icon="❄️",
                 asset_key="frostbite", description="Transparent icy-blue body with chiseled crystal grip and cold frost aura."),

            dict(name="Neon Pulse", rarity="rare", price_pp=2600,
                 body_color="#10b981", accent_color="#d8b4fe", ink_color="#047857", trail_color="#34d399", icon="🎧",
                 asset_key="neon-pulse", description="Equalizer pulse-line pen with high-contrast neon green and magenta body."),

            dict(name="Ocean Phantom", rarity="rare", price_pp=2800,
                 body_color="#0d9488", accent_color="#99f6e4", ink_color="#115e59", trail_color="#2dd4bf", icon="🌊",
                 asset_key="ocean-phantom", description="Deep sea turquoise body with flowing wave patterns and pearl clip."),

            dict(name="Sakura", rarity="rare", price_pp=3000,
                 body_color="#fbcfe8", accent_color="#f43f5e", ink_color="#e11d48", trail_color="#fda4af", icon="🌸",
                 asset_key="sakura", description="Pearl white barrel decorated with cherry blossom petals and rose gold clip."),

            dict(name="Inferno", rarity="epic", price_pp=4500, glow=True, is_featured=True,
                 body_color="#18181b", accent_color="#ef4444", ink_color="#7f1d1d", trail_color="#f87171", icon="🔥",
                 asset_key="inferno", description="Matte black metallic body with pulsing magma red energy channels."),

            dict(name="Thunderbolt", rarity="epic", price_pp=5000, glow=True, is_featured=True,
                 body_color="#334155", accent_color="#facc15", ink_color="#854d0e", trail_color="#fef08a", icon="⚡",
                 asset_key="thunderbolt", description="Dark graphite hexagonal body with yellow electric circuitry and lightning clip."),

            dict(name="Galaxy", rarity="epic", price_pp=6000, glow=True, is_featured=True,
                 body_color="#4c1d95", accent_color="#c084fc", ink_color="#3b0764", trail_color="#a78bfa", icon="🌌",
                 asset_key="galaxy", description="Deep purple cosmic body filled with galaxy nebula texture and star dust."),

            dict(name="Cyber-X", rarity="epic", price_pp=6500, glow=True,
                 body_color="#09090b", accent_color="#06b6d4", ink_color="#155e75", trail_color="#22d3ee", icon="🤖",
                 asset_key="cyber-x", description="Cyberpunk matte black chassis with cyan and magenta neon light channels."),

            dict(name="Toxic Venom", rarity="epic", price_pp=6800, glow=True,
                 body_color="#15803d", accent_color="#a3e635", ink_color="#3f6212", trail_color="#84cc16", icon="☣️",
                 asset_key="toxic-venom", description="Biohazard striped pen housing a translucent glowing green slime reservoir."),

            dict(name="Holographic", rarity="epic", price_pp=7200, glow=True,
                 body_color="#38bdf8", accent_color="#f472b6", ink_color="#0284c7", trail_color="#c084fc", icon="🪞",
                 asset_key="holographic", description="Iridescent rainbow-chromatic barrel with light-shifting prism reflections."),

            dict(name="Golden Royal", rarity="legendary", price_pp=9000, glow=True, is_featured=True,
                 body_color="#eab308", accent_color="#fef9c3", ink_color="#854d0e", trail_color="#facc15", icon="👑",
                 asset_key="golden-royal", description="Polished 24K gold body with black quilted leather grip and ruby crown clip."),

            dict(name="Shadow Reaper", rarity="legendary", price_pp=9800, glow=True,
                 body_color="#0f172a", accent_color="#a855f7", ink_color="#1e1b4b", trail_color="#7e22ce", icon="💀",
                 asset_key="shadow-reaper", description="Dark obsidian metallic armor body with scythe clip and dark energy aura."),

            dict(name="Samurai", rarity="legendary", price_pp=10500, glow=True,
                 body_color="#991b1b", accent_color="#e2e8f0", ink_color="#7f1d1d", trail_color="#f59e0b", icon="⚔️",
                 asset_key="samurai", description="Katana-inspired steel barrel with traditional crimson tsuka-ito braided grip wrap."),

            dict(name="Ancient Gold", rarity="legendary", price_pp=11000, glow=True,
                 body_color="#ca8a04", accent_color="#0284c7", ink_color="#854d0e", trail_color="#eab308", icon="🏺",
                 asset_key="ancient-gold", description="Egyptian gold & lapis lazuli body engraved with ancient hieroglyphics and scarab clip."),

            dict(name="Dragon Fang", rarity="mythic", price_pp=14000, glow=True, is_featured=True,
                 body_color="#7f1d1d", accent_color="#f59e0b", ink_color="#991b1b", trail_color="#b91c1c", icon="🐉",
                 asset_key="dragon-fang", description="Mythic dragon-scale body featuring a dragon-head clip with glowing red eyes."),

            dict(name="Cosmic Void", rarity="mythic", price_pp=16000, glow=True,
                 body_color="#030712", accent_color="#f8fafc", ink_color="#000000", trail_color="#94a3b8", icon="🕳️",
                 asset_key="cosmic-void", description="Singularity pitch-black body bounded by an event horizon glowing white edge."),

            dict(name="Plasma Core", rarity="mythic", price_pp=18000, glow=True, is_featured=True,
                 body_color="#1e1b4b", accent_color="#38bdf8", ink_color="#1d4ed8", trail_color="#60a5fa", icon="⚛️",
                 asset_key="plasma-core", description="Translucent containment barrel housing a pulsating blue-white plasma arc core."),
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
