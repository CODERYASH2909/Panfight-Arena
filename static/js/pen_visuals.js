/* =========================================================================
   PENFIGHT ARENA — Pen Visuals Engine
   Generates authentic, highly detailed 2D/2.5D vector Ball Pens.
   Supports SVG output (for store cards, modals, icons) and Canvas output
   (for real-time battle rendering and 3D hero preview rotation).
   ========================================================================= */

window.PenVisuals = (function () {
  // Comprehensive skin visual metadata & geometry properties
  const SKINS = {
    "classic-blue": {
      name: "Classic Blue",
      bodyColor: "#2563eb", accentColor: "#93c5fd", gripColor: "#1d4ed8",
      tipColor: "#cbd5e1", clipColor: "#94a3b8", inkColor: "#1e40af",
      translucent: true, pattern: "smooth", style: "ballpen-classic"
    },
    "forest-guardian": {
      name: "Forest Guardian",
      bodyColor: "#14532d", accentColor: "#86efac", gripColor: "#15803d",
      tipColor: "#d97706", clipColor: "#b45309", inkColor: "#166534",
      translucent: false, pattern: "vines", style: "ballpen-organic"
    },
    "sunset-blaze": {
      name: "Sunset Blaze",
      bodyColor: "#ea580c", accentColor: "#fef08a", gripColor: "#c2410c",
      tipColor: "#eab308", clipColor: "#ca8a04", inkColor: "#9a3412",
      translucent: false, pattern: "gradient-fire", style: "ballpen-sport"
    },
    "frostbite": {
      name: "Frostbite",
      bodyColor: "#0284c7", accentColor: "#e0f2fe", gripColor: "#0369a1",
      tipColor: "#e2e8f0", clipColor: "#bae6fd", inkColor: "#075985",
      translucent: true, pattern: "frost-crystals", style: "ballpen-crystal"
    },
    "inferno": {
      name: "Inferno",
      bodyColor: "#18181b", accentColor: "#ef4444", gripColor: "#991b1b",
      tipColor: "#52525b", clipColor: "#dc2626", inkColor: "#7f1d1d",
      translucent: false, pattern: "magma-lines", style: "ballpen-tactical"
    },
    "thunderbolt": {
      name: "Thunderbolt",
      bodyColor: "#334155", accentColor: "#facc15", gripColor: "#eab308",
      tipColor: "#e2e8f0", clipColor: "#fef08a", inkColor: "#854d0e",
      translucent: false, pattern: "circuit-bolt", style: "ballpen-tech"
    },
    "galaxy": {
      name: "Galaxy",
      bodyColor: "#4c1d95", accentColor: "#c084fc", gripColor: "#5b21b6",
      tipColor: "#a855f7", clipColor: "#e9d5ff", inkColor: "#3b0764",
      translucent: true, pattern: "nebula-stars", style: "ballpen-cosmic"
    },
    "cyber-x": {
      name: "Cyber-X",
      bodyColor: "#09090b", accentColor: "#06b6d4", gripColor: "#ec4899",
      tipColor: "#22d3ee", clipColor: "#f43f5e", inkColor: "#155e75",
      translucent: false, pattern: "cyber-grid", style: "ballpen-cyber"
    },
    "golden-royal": {
      name: "Golden Royal",
      bodyColor: "#eab308", accentColor: "#fef9c3", gripColor: "#18181b",
      tipColor: "#facc15", clipColor: "#ef4444", inkColor: "#854d0e",
      translucent: false, pattern: "royal-engraving", style: "ballpen-luxury"
    },
    "shadow-reaper": {
      name: "Shadow Reaper",
      bodyColor: "#0f172a", accentColor: "#a855f7", gripColor: "#3b0764",
      tipColor: "#475569", clipColor: "#7e22ce", inkColor: "#1e1b4b",
      translucent: false, pattern: "dark-energy", style: "ballpen-reaper"
    },
    "dragon-fang": {
      name: "Dragon Fang",
      bodyColor: "#7f1d1d", accentColor: "#f59e0b", gripColor: "#450a0a",
      tipColor: "#b91c1c", clipColor: "#fbbf24", inkColor: "#991b1b",
      translucent: false, pattern: "dragon-scales", style: "ballpen-dragon"
    },
    "neon-pulse": {
      name: "Neon Pulse",
      bodyColor: "#10b981", accentColor: "#d8b4fe", gripColor: "#059669",
      tipColor: "#a855f7", clipColor: "#34d399", inkColor: "#047857",
      translucent: false, pattern: "pulse-equalizer", style: "ballpen-tech"
    },
    "ocean-phantom": {
      name: "Ocean Phantom",
      bodyColor: "#0d9488", accentColor: "#99f6e4", gripColor: "#0f766e",
      tipColor: "#ccfbf1", clipColor: "#2dd4bf", inkColor: "#115e59",
      translucent: true, pattern: "waves", style: "ballpen-organic"
    },
    "toxic-venom": {
      name: "Toxic Venom",
      bodyColor: "#15803d", accentColor: "#a3e635", gripColor: "#166534",
      tipColor: "#84cc16", clipColor: "#bef264", inkColor: "#3f6212",
      translucent: true, pattern: "biohazard", style: "ballpen-tactical"
    },
    "samurai": {
      name: "Samurai",
      bodyColor: "#991b1b", accentColor: "#e2e8f0", gripColor: "#18181b",
      tipColor: "#f59e0b", clipColor: "#e2e8f0", inkColor: "#7f1d1d",
      translucent: false, pattern: "tsuka-braid", style: "ballpen-samurai"
    },
    "stealth": {
      name: "Stealth",
      bodyColor: "#1e293b", accentColor: "#64748b", gripColor: "#0f172a",
      tipColor: "#334155", clipColor: "#475569", inkColor: "#020617",
      translucent: false, pattern: "carbon-fiber", style: "ballpen-tactical"
    },
    "holographic": {
      name: "Holographic",
      bodyColor: "#38bdf8", accentColor: "#f472b6", gripColor: "#c084fc",
      tipColor: "#fef08a", clipColor: "#e0e7ff", inkColor: "#0284c7",
      translucent: true, pattern: "rainbow-hologram", style: "ballpen-crystal"
    },
    "cosmic-void": {
      name: "Cosmic Void",
      bodyColor: "#030712", accentColor: "#f8fafc", gripColor: "#111827",
      tipColor: "#94a3b8", clipColor: "#f1f5f9", inkColor: "#000000",
      translucent: false, pattern: "event-horizon", style: "ballpen-reaper"
    },
    "sakura": {
      name: "Sakura",
      bodyColor: "#fbcfe8", accentColor: "#f43f5e", gripColor: "#f472b6",
      tipColor: "#fb7185", clipColor: "#fda4af", inkColor: "#e11d48",
      translucent: false, pattern: "sakura-petals", style: "ballpen-organic"
    },
    "ancient-gold": {
      name: "Ancient Gold",
      bodyColor: "#ca8a04", accentColor: "#0284c7", gripColor: "#1e3a8a",
      tipColor: "#eab308", clipColor: "#fef08a", inkColor: "#854d0e",
      translucent: false, pattern: "hieroglyphs", style: "ballpen-luxury"
    },
    "plasma-core": {
      name: "Plasma Core",
      bodyColor: "#1e1b4b", accentColor: "#38bdf8", gripColor: "#312e81",
      tipColor: "#60a5fa", clipColor: "#93c5fd", inkColor: "#1d4ed8",
      translucent: true, pattern: "plasma-conduit", style: "ballpen-tech"
    }
  };

  function getSkinData(key) {
    return SKINS[key] || SKINS["classic-blue"];
  }

  // =========================================================================
  // 1. SVG GENERATOR (Renders full-resolution vector ball pen as SVG string)
  // =========================================================================
  function renderSVG(key, opts = {}) {
    const s = getSkinData(key);
    const width = opts.width || 340;
    const height = opts.height || 100;
    const angle = opts.angle || 0; // degrees

    // Render horizontal pen layout (length ~260, height ~40) centered in SVG
    const penLength = 260;
    const penHeight = 34;

    const bColor = s.bodyColor;
    const aColor = s.accentColor;
    const gColor = s.gripColor;
    const tColor = s.tipColor;
    const cColor = s.clipColor;
    const iColor = s.inkColor;

    const uniqueId = "pen_" + key.replace(/[^a-z0-9]/g, "_") + "_" + Math.floor(Math.random()*10000);

    let defs = `
      <defs>
        <linearGradient id="${uniqueId}_body" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="${aColor}" stop-opacity="0.9"/>
          <stop offset="35%" stop-color="${bColor}"/>
          <stop offset="85%" stop-color="${bColor}"/>
          <stop offset="100%" stop-color="#000000" stop-opacity="0.4"/>
        </linearGradient>

        <linearGradient id="${uniqueId}_tip" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#ffffff"/>
          <stop offset="40%" stop-color="${tColor}"/>
          <stop offset="100%" stop-color="#334155"/>
        </linearGradient>

        <linearGradient id="${uniqueId}_clip" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#ffffff"/>
          <stop offset="50%" stop-color="${cColor}"/>
          <stop offset="100%" stop-color="#1e293b"/>
        </linearGradient>

        <filter id="${uniqueId}_glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
    `;

    // Distinct geometric parts based on skin style
    let penElements = "";

    // A. Click Button / Back Cap (Left end: X=20 to X=45)
    if (s.style === "ballpen-tactical" || s.style === "ballpen-tech") {
      penElements += `
        <!-- Angular Mechanical Clicker -->
        <polygon points="20,13 32,13 36,17 36,33 32,37 20,37" fill="url(#${uniqueId}_tip)"/>
        <rect x="36" y="15" width="8" height="20" rx="2" fill="${cColor}"/>
      `;
    } else if (s.style === "ballpen-luxury" || s.style === "ballpen-reaper") {
      penElements += `
        <!-- Crown/Jewel Button -->
        <rect x="18" y="14" width="16" height="22" rx="4" fill="url(#${uniqueId}_tip)"/>
        <circle cx="20" cy="25" r="5" fill="${aColor}" filter="url(#${uniqueId}_glow)"/>
        <rect x="34" y="13" width="8" height="24" rx="2" fill="url(#${uniqueId}_clip)"/>
      `;
    } else if (s.style === "ballpen-dragon") {
      penElements += `
        <!-- Dragon Skull Cap -->
        <path d="M 18 16 Q 28 10 38 16 L 42 25 L 38 34 Q 28 40 18 34 Z" fill="#450a0a" stroke="${aColor}" stroke-width="1.5"/>
      `;
    } else {
      penElements += `
        <!-- Standard Rounded Push Button -->
        <rect x="18" y="15" width="18" height="20" rx="6" fill="url(#${uniqueId}_tip)"/>
        <rect x="32" y="13" width="8" height="24" rx="2" fill="url(#${uniqueId}_clip)"/>
      `;
    }

    // B. Main Barrel (X=42 to X=200)
    let barrelShape = "";
    if (s.style === "ballpen-tactical") {
      barrelShape = `
        <polygon points="42,12 190,14 200,16 200,34 190,36 42,38" fill="url(#${uniqueId}_body)"/>
        <!-- Tactical Ribbed Cuts -->
        <line x1="60" y1="12" x2="60" y2="38" stroke="#000" stroke-width="2" opacity="0.4"/>
        <line x1="80" y1="12" x2="80" y2="38" stroke="#000" stroke-width="2" opacity="0.4"/>
        <line x1="100" y1="12" x2="100" y2="38" stroke="#000" stroke-width="2" opacity="0.4"/>
      `;
    } else if (s.style === "ballpen-crystal") {
      barrelShape = `
        <!-- Faceted Crystal Barrel -->
        <polygon points="42,13 195,15 195,35 42,37" fill="url(#${uniqueId}_body)"/>
        <polygon points="42,13 195,15 195,22 42,21" fill="${aColor}" opacity="0.45"/>
        <polygon points="42,28 195,29 195,35 42,37" fill="#000" opacity="0.25"/>
      `;
    } else if (s.style === "ballpen-dragon") {
      barrelShape = `
        <!-- Dragon Scale Barrel -->
        <rect x="42" y="13" width="153" height="24" rx="4" fill="url(#${uniqueId}_body)"/>
        <!-- Scale Overlays -->
        <path d="M 50 15 Q 60 25 70 15 M 70 15 Q 80 25 90 15 M 90 15 Q 100 25 110 15 M 110 15 Q 120 25 130 15" stroke="${aColor}" stroke-width="1.5" fill="none" opacity="0.7"/>
        <path d="M 60 25 Q 70 35 80 25 M 80 25 Q 90 35 100 25 M 100 25 Q 110 35 120 25 M 120 25 Q 130 35 140 25" stroke="${aColor}" stroke-width="1.5" fill="none" opacity="0.7"/>
      `;
    } else {
      barrelShape = `
        <!-- Smooth Tapered Barrel -->
        <rect x="42" y="13" width="153" height="24" rx="8" fill="url(#${uniqueId}_body)"/>
        <!-- Highlight reflection -->
        <rect x="45" y="16" width="145" height="4" rx="2" fill="#ffffff" opacity="0.35"/>
      `;
    }
    penElements += barrelShape;

    // Translucent Refill Ink Tube (if translucent skin)
    if (s.translucent) {
      penElements += `
        <!-- Translucent Inner Refill Tube & Spring -->
        <rect x="55" y="22" width="125" height="6" rx="3" fill="${iColor}" opacity="0.85"/>
        <!-- Coiled Spring at tip end -->
        <path d="M 175 20 L 177 30 M 179 20 L 181 30 M 183 20 L 185 30" stroke="${tColor}" stroke-width="1.5"/>
      `;
    }

    // Specific Pattern Details
    if (s.pattern === "vines") {
      penElements += `<path d="M 50 25 C 70 15, 90 35, 110 25 C 130 15, 150 35, 170 25" stroke="${aColor}" stroke-width="2" fill="none" stroke-dasharray="4,2"/>`;
    } else if (s.pattern === "circuit-bolt") {
      penElements += `<path d="M 50 18 L 70 18 L 75 28 L 100 28 L 105 18 L 140 18 L 145 28 L 170 28" stroke="${aColor}" stroke-width="2" fill="none"/>`;
    } else if (s.pattern === "cyber-grid") {
      penElements += `<path d="M 50 15 L 180 15 M 50 25 L 180 25 M 50 35 L 180 35" stroke="${aColor}" stroke-width="1" opacity="0.4" stroke-dasharray="6,4"/>`;
    } else if (s.pattern === "royal-engraving" || s.pattern === "hieroglyphs") {
      penElements += `<circle cx="80" cy="25" r="4" fill="none" stroke="${aColor}" stroke-width="1.5"/><circle cx="120" cy="25" r="4" fill="none" stroke="${aColor}" stroke-width="1.5"/><circle cx="160" cy="25" r="4" fill="none" stroke="${aColor}" stroke-width="1.5"/>`;
    } else if (s.pattern === "magma-lines" || s.pattern === "dark-energy") {
      penElements += `<path d="M 50 30 L 80 16 L 110 32 L 140 17 L 170 30" stroke="${aColor}" stroke-width="2" fill="none" filter="url(#${uniqueId}_glow)"/>`;
    }

    // C. Ergonomic Grip Section (X=195 to X=240)
    let gripShape = "";
    if (s.style === "ballpen-samurai") {
      // Braided katana tsuka grip
      gripShape = `
        <rect x="195" y="14" width="45" height="22" fill="${gColor}"/>
        <path d="M 195 14 L 205 36 M 205 14 L 215 36 M 215 14 L 225 36 M 225 14 L 235 36" stroke="${aColor}" stroke-width="2"/>
        <path d="M 205 14 L 195 36 M 215 14 L 205 36 M 225 14 L 215 36 M 235 14 L 225 36" stroke="${aColor}" stroke-width="2"/>
      `;
    } else {
      // Ribbed rubber / textured grip
      gripShape = `
        <rect x="195" y="14" width="45" height="22" rx="4" fill="${gColor}"/>
        <!-- Ribbed texture grooves -->
        <line x1="203" y1="14" x2="203" y2="36" stroke="#000" stroke-width="1.5" opacity="0.4"/>
        <line x1="211" y1="14" x2="211" y2="36" stroke="#000" stroke-width="1.5" opacity="0.4"/>
        <line x1="219" y1="14" x2="219" y2="36" stroke="#000" stroke-width="1.5" opacity="0.4"/>
        <line x1="227" y1="14" x2="227" y2="36" stroke="#000" stroke-width="1.5" opacity="0.4"/>
        <line x1="235" y1="14" x2="235" y2="36" stroke="#000" stroke-width="1.5" opacity="0.4"/>
      `;
    }
    penElements += gripShape;

    // D. Metal Tip Cone & Ball Point (X=240 to X=280)
    let tipShape = "";
    if (s.style === "ballpen-reaper" || s.style === "ballpen-dragon") {
      // Aggressive Spike Cone
      tipShape = `
        <polygon points="240,14 275,23 275,27 240,36" fill="url(#${uniqueId}_tip)"/>
        <!-- Ball Point tungsten tip -->
        <circle cx="277" cy="25" r="2" fill="#0f172a"/>
      `;
    } else {
      // Smooth Precision Cone
      tipShape = `
        <path d="M 240 14 Q 255 17 274 23 L 274 27 Q 255 33 240 36 Z" fill="url(#${uniqueId}_tip)"/>
        <rect x="238" y="13" width="4" height="24" rx="1" fill="url(#${uniqueId}_clip)"/>
        <!-- Ball Point -->
        <circle cx="276" cy="25" r="1.8" fill="#1e293b"/>
      `;
    }
    penElements += tipShape;

    // E. Pocket Clip (Extends along barrel X=34 to X=120)
    let clipShape = "";
    if (s.style === "ballpen-reaper") {
      // Scythe Clip
      clipShape = `
        <path d="M 36 12 L 110 8 Q 125 4 120 16 L 105 14 L 36 14 Z" fill="url(#${uniqueId}_clip)" filter="url(#${uniqueId}_glow)"/>
      `;
    } else if (s.style === "ballpen-dragon") {
      // Dragon Head Clip
      clipShape = `
        <path d="M 36 11 L 115 11 Q 125 15 118 20 L 108 14 L 36 14 Z" fill="url(#${uniqueId}_clip)"/>
        <circle cx="116" cy="14" r="2" fill="#ef4444" filter="url(#${uniqueId}_glow)"/>
      `;
    } else {
      // Streamlined Metallic Clip
      clipShape = `
        <path d="M 36 12 L 125 12 Q 132 12 130 16 Q 125 16 120 15 L 36 15 Z" fill="url(#${uniqueId}_clip)"/>
        <circle cx="127" cy="14" r="2" fill="${aColor}"/>
      `;
    }
    penElements += clipShape;

    // F. Ambient Glow / Particles for Special Skins
    let particles = "";
    if (key === "inferno" || key === "sunset-blaze" || key === "dragon-fang") {
      particles = `
        <circle cx="90" cy="10" r="2.5" fill="#f97316" opacity="0.8"/>
        <circle cx="150" cy="38" r="2" fill="#ef4444" opacity="0.8"/>
        <circle cx="230" cy="8" r="3" fill="#facc15" opacity="0.9"/>
      `;
    } else if (key === "thunderbolt" || key === "cyber-x" || key === "plasma-core") {
      particles = `
        <circle cx="120" cy="8" r="2" fill="#06b6d4" opacity="0.9"/>
        <circle cx="180" cy="40" r="2.5" fill="#facc15" opacity="0.9"/>
      `;
    } else if (key === "galaxy" || key === "cosmic-void" || key === "holographic") {
      particles = `
        <circle cx="70" cy="8" r="2" fill="#e9d5ff" opacity="0.9"/>
        <circle cx="140" cy="40" r="1.8" fill="#a855f7" opacity="0.9"/>
        <circle cx="210" cy="7" r="2.2" fill="#f472b6" opacity="0.9"/>
      `;
    } else if (key === "golden-royal" || key === "ancient-gold") {
      particles = `
        <polygon points="100,6 103,11 108,11 104,14 106,19 100,16 94,19 96,14 92,11 97,11" fill="#facc15" opacity="0.85"/>
        <polygon points="220,38 222,41 226,41 223,43 224,47 220,45 216,47 217,43 214,41 218,41" fill="#fef08a" opacity="0.85"/>
      `;
    }

    return `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 50" width="${width}" height="${height}" style="transform: rotate(${angle}deg); overflow: visible;">
        ${defs}
        <g filter="${s.pattern.includes('glow') || s.style.includes('reaper') || s.style.includes('dragon') ? `url(#${uniqueId}_glow)` : ''}">
          ${penElements}
          ${particles}
        </g>
      </svg>
    `;
  }

  // =========================================================================
  // 2. CANVAS ENGINE RENDERER (Renders high-fidelity pen directly to Canvas)
  // =========================================================================
  function drawPenToCanvas(ctx, key, x, y, angleRad, scale = 1, opts = {}) {
    const s = getSkinData(key);

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angleRad);
    ctx.scale(scale, scale);

    const L = opts.length || 76;
    const W = opts.width || 16;

    // Optional Glow
    if (s.pattern.includes("glow") || s.style === "ballpen-reaper" || s.style === "ballpen-dragon" || s.style === "ballpen-tech") {
      ctx.shadowColor = s.accentColor;
      ctx.shadowBlur = 18;
    }

    // 1. Barrel Body (-L/2 to +L*0.25)
    const bodyGrad = ctx.createLinearGradient(-L / 2, 0, L * 0.25, 0);
    bodyGrad.addColorStop(0, s.accentColor);
    bodyGrad.addColorStop(0.5, s.bodyColor);
    bodyGrad.addColorStop(1, s.bodyColor);

    ctx.fillStyle = bodyGrad;
    ctx.beginPath();
    ctx.roundRect(-L / 2, -W / 2, L * 0.72, W, W / 2);
    ctx.fill();

    // Body Texture lines
    ctx.strokeStyle = "rgba(255,255,255,0.25)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 2. Refill / Ink Tube detail if translucent
    if (s.translucent) {
      ctx.fillStyle = s.inkColor;
      ctx.fillRect(-L * 0.35, -W * 0.15, L * 0.5, W * 0.3);
    }

    // 3. Ergonomic Grip (-L*0.05 to +L*0.22)
    ctx.fillStyle = s.gripColor;
    ctx.beginPath();
    ctx.roundRect(-L * 0.05, -W * 0.52, L * 0.26, W * 1.04, 3);
    ctx.fill();

    // Grip rib lines
    ctx.strokeStyle = "rgba(0,0,0,0.35)";
    ctx.lineWidth = 1;
    for (let r = -L * 0.02; r < L * 0.2; r += 4) {
      ctx.beginPath();
      ctx.moveTo(r, -W * 0.5);
      ctx.lineTo(r, W * 0.5);
      ctx.stroke();
    }

    // 4. Precision Metallic Tip Cone (+L*0.22 to +L*0.5)
    const tipGrad = ctx.createLinearGradient(L * 0.22, 0, L * 0.5, 0);
    tipGrad.addColorStop(0, s.tipColor);
    tipGrad.addColorStop(0.8, "#ffffff");
    tipGrad.addColorStop(1, "#1e293b");

    ctx.fillStyle = tipGrad;
    ctx.beginPath();
    ctx.moveTo(L * 0.22, -W / 2);
    ctx.lineTo(L * 0.5, 0);
    ctx.lineTo(L * 0.22, W / 2);
    ctx.closePath();
    ctx.fill();

    // Tungsten ball tip point
    ctx.fillStyle = "#0f172a";
    ctx.beginPath();
    ctx.arc(L * 0.5 + 1, 0, 1.8, 0, Math.PI * 2);
    ctx.fill();

    // 5. Back Push Button / Cap (-L/2 - 6 to -L/2)
    ctx.fillStyle = s.clipColor;
    ctx.fillRect(-L / 2 - 5, -W * 0.35, 6, W * 0.7);

    // 6. Metallic Pocket Clip (-L/2 + 4 to -L*0.1)
    ctx.fillStyle = s.clipColor;
    ctx.beginPath();
    ctx.roundRect(-L / 2 + 4, -W / 2 - 3, L * 0.38, 3, 1.5);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.restore();
  }

  return {
    SKINS,
    getSkinData,
    renderSVG,
    drawPenToCanvas
  };
})();
