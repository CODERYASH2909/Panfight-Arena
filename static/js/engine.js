/* =========================================================================
   PENFIGHT ARENA — Physics Engine v5 (Authoritative Full Tabletop)
   - Playable table occupies ~94% of canvas (authoritative TABLE_BOUNDS)
   - Heavy pen baseline physics for ALL pens (NORMAL = 2.5, HEAVY = 4.0)
   - Soft quadratic power curve (Exponent 2.0) & low velocity cap (75 px/s)
   - 100% max power takes 2.5–4.0s of heavy visible sliding motion
   - Fixed 60Hz timestep sub-stepping to prevent frame-rate dependent forces
   ========================================================================= */

const PHYSICS = {
  NORMAL_PEN_MASS: 2.5,     // Heavy baseline mass for all standard pens
  HEAVY_PEN_MASS: 4.0,      // Heavy Pen archetype mass (extra heavy)
  MIN_FLICK_FORCE: 5.0,     // 5% power force (creeps ~10-20px)
  MAX_FLICK_FORCE: 55.0,    // 100% power force
  POWER_EXPONENT: 2.0,      // Soft quadratic power curve (power^2)
  FRICTION: 0.935,          // Strong realistic desk surface friction
  ANGULAR_FRICTION: 0.85,   // Rotation damping
  MIN_SPEED: 1.2,           // Settling threshold below which motion stops
  RESTITUTION: 0.52,        // Pen-to-pen bounce elasticity (low bounce)
  BUMPER_RESTITUTION: 0.70, // Bumper vector reflection elasticity
  KNOCKBACK_SCALE: 0.45,    // Reduced collision displacement multiplier
  EDGE_MARGIN: 8,           // Collision body edge fall offset
  MAX_PEN_VELOCITY: 75.0,   // Low maximum speed cap (75.0 px/s)
  FIXED_DT: 1 / 60,         // Fixed 60Hz physics timestep
};

class PenFightEngine {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Object} opts
   *   bench: optional override {x,y,w,h}
   *   onSettle: fn({penId, x, y, angle})
   *   onFall: fn(penId)
   *   onCollision: fn(penIdA, penIdB, strength)
   *   onBumperHit: fn(bumper, strength)
   */
  constructor(canvas, opts = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSettle = opts.onSettle || (() => {});
    this.onFall = opts.onFall || (() => {});
    this.onCollision = opts.onCollision || (() => {});
    this.onBumperHit = opts.onBumperHit || (() => {});

    // Compute single authoritative TABLE_BOUNDS from canvas (~94% viewport)
    this.bench = opts.bench || this.getPlayableTableBounds();

    this.pens = {};
    this.bumpers = [];
    this.particles = [];
    this.running = false;
    this.settledPending = new Set();
    this.debugMode = false;
    this._accumulator = 0;
    this._loop = this._loop.bind(this);

    // Visual Constants
    this.PEN_LENGTH = 74;
    this.PEN_WIDTH = 15;

    // Listen for debug key (D)
    window.addEventListener("keydown", (e) => {
      if (e.key === "d" || e.key === "D") {
        this.debugMode = !this.debugMode;
      }
    });
  }

  /** Calculate responsive playable table bounds occupying ~94% of canvas */
  getPlayableTableBounds() {
    const W = this.canvas.width || 960;
    const H = this.canvas.height || 520;
    const marginX = Math.round(W * 0.025); // ~24px on 960px canvas
    const marginY = Math.round(H * 0.03);  // ~15px on 520px canvas
    return {
      x: marginX,
      y: marginY,
      w: W - marginX * 2, // ~912px
      h: H - marginY * 2, // ~490px
    };
  }

  addPen(id, { x, y, angle = 0, color = "#3b82f6", accent = "#93c5fd", trailColor = "#60a5fa", glow = false, mass = 1, friction = 1, icon = "", assetKey = "classic-blue" }) {
    // Heavy pen baseline physics
    const effectiveMass = (mass > 1.3) ? PHYSICS.HEAVY_PEN_MASS : PHYSICS.NORMAL_PEN_MASS * (mass || 1.0);
    this.pens[id] = {
      id, x, y, angle,
      vx: 0, vy: 0, angularVel: 0,
      mass: effectiveMass, frictionMult: friction,
      color, accent, trailColor, glow, icon, assetKey,
      alive: true, falling: false, fallProgress: 0, fallVX: 0,
      trail: [],
    };
  }

  removePen(id) { delete this.pens[id]; }

  /** Generate random procedural bumpers across full tabletop bounds */
  generateBumpers(seed = Math.random()) {
    this.bumpers = [];
    const b = this.bench;
    const penList = Object.values(this.pens);
    const types = ["wood", "rubber", "metal", "stationery"];

    let s = typeof seed === "string" ? this._hashSeed(seed) : seed;
    const rand = () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };

    const count = 3 + Math.floor(rand() * 3); // 3 to 5 bumpers
    const safetyRadius = 140; // 140px clearance around starting pens
    const edgeMargin = 65;

    for (let attempts = 0; attempts < 60 && this.bumpers.length < count; attempts++) {
      const type = types[Math.floor(rand() * types.length)];
      const isCircle = type === "stationery";
      const bw = isCircle ? 36 : 44 + Math.floor(rand() * 24);
      const bh = isCircle ? 36 : 22 + Math.floor(rand() * 12);
      const angle = isCircle ? 0 : (rand() - 0.5) * 0.7;

      const bx = b.x + edgeMargin + rand() * (b.w - edgeMargin * 2 - bw);
      const by = b.y + edgeMargin + rand() * (b.h - edgeMargin * 2 - bh);

      // Rule 1: Safety clearance from starting pens
      const nearPen = penList.some((p) => Math.hypot(p.x - bx, p.y - by) < safetyRadius);
      if (nearPen) continue;

      // Rule 2: Separation between bumpers
      const nearBumper = this.bumpers.some((other) => Math.hypot(other.x - bx, other.y - by) < 100);
      if (nearBumper) continue;

      // Rule 3: Clear central direct corridor
      const centerDistY = Math.abs(by - (b.y + b.h / 2));
      const centerDistX = Math.abs(bx - (b.x + b.w / 2));
      if (centerDistY < 35 && centerDistX < 160) continue;

      this.bumpers.push({ id: `bmp_${this.bumpers.length}`, type, x: bx, y: by, w: bw, h: bh, isCircle, angle });
    }
  }

  _hashSeed(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) hash = (hash << 5) - hash + str.charCodeAt(i) | 0;
    return Math.abs(hash) / 2147483647;
  }

  /** Apply single non-linear flick impulse to a pen */
  flick(id, angleRad, rawPower) {
    const pen = this.pens[id];
    if (!pen || !pen.alive) return;

    // Soft quadratic power curve (Exponent 2.0)
    const normPower = Math.max(0, Math.min(1, rawPower));
    const scaledPower = Math.pow(normPower, PHYSICS.POWER_EXPONENT);
    const force = PHYSICS.MIN_FLICK_FORCE + scaledPower * (PHYSICS.MAX_FLICK_FORCE - PHYSICS.MIN_FLICK_FORCE);

    // Initial Velocity = Force / (Mass / NORMAL_PEN_MASS)
    const massRatio = (pen.mass || PHYSICS.NORMAL_PEN_MASS) / PHYSICS.NORMAL_PEN_MASS;
    const initialSpeed = Math.min(PHYSICS.MAX_PEN_VELOCITY, force / massRatio);

    pen.vx = Math.cos(angleRad) * initialSpeed;
    pen.vy = Math.sin(angleRad) * initialSpeed;
    pen.angularVel = (Math.random() - 0.5) * 0.04 * normPower;
    this.settledPending.add(id);
  }

  setState(id, { x, y, angle, vx = 0, vy = 0 }) {
    const pen = this.pens[id];
    if (!pen) return;
    pen.x = x; pen.y = y; pen.angle = angle; pen.vx = vx; pen.vy = vy;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this._lastTs = performance.now();
    this._accumulator = 0;
    requestAnimationFrame(this._loop);
  }

  stop() { this.running = false; }

  _loop(ts) {
    if (!this.running) return;
    const frameTime = Math.min(50, ts - this._lastTs) / 1000;
    this._lastTs = ts;
    this._accumulator += frameTime;

    // Fixed 60Hz sub-stepping physics integration
    while (this._accumulator >= PHYSICS.FIXED_DT) {
      this._update(1.0);
      this._accumulator -= PHYSICS.FIXED_DT;
    }

    this._render();
    requestAnimationFrame(this._loop);
  }

  _update(dt) {
    const ids = Object.keys(this.pens);

    for (const id of ids) {
      const p = this.pens[id];
      if (!p.alive) continue;

      if (p.falling) {
        p.fallProgress += 0.02 * dt;
        p.y += 2.0 * dt * p.fallProgress;
        p.angle += 0.06 * dt;
        p.x += p.fallVX * dt * 0.2;
        if (p.fallProgress >= 1.5) {
          p.alive = false;
          this.onFall(id);
        }
        continue;
      }

      const speed = Math.hypot(p.vx, p.vy);
      if (speed > 0.05) {
        if (speed > 25 && Math.random() < 0.3) {
          p.trail.push({ x: p.x, y: p.y, life: 1 });
        }

        p.x += p.vx * dt * 0.1667;
        p.y += p.vy * dt * 0.1667;
        p.angle += p.angularVel * dt;

        // Friction damping
        const fr = Math.pow(PHYSICS.FRICTION / (p.frictionMult * 0.98), dt);
        p.vx *= fr; p.vy *= fr;
        p.angularVel *= Math.pow(PHYSICS.ANGULAR_FRICTION, dt);

        if (Math.hypot(p.vx, p.vy) < PHYSICS.MIN_SPEED) {
          p.vx = 0; p.vy = 0; p.angularVel = 0;
          if (this.settledPending.has(id)) {
            this.settledPending.delete(id);
            this.onSettle({ penId: id, x: p.x, y: p.y, angle: p.angle });
          }
        }
      }

      p.trail.forEach((t) => (t.life -= 0.04 * dt));
      p.trail = p.trail.filter((t) => t.life > 0);

      // Edge fall check against authoritative bench bounds
      if (this._isPastEdge(p)) {
        p.falling = true;
        p.fallVX = p.vx * 0.2;
      }

      // Bumper bounce check
      this._resolveBumperCollisions(p);
    }

    // Pairwise pen-to-pen collisions
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = this.pens[ids[i]], b = this.pens[ids[j]];
        if (!a.alive || !b.alive || a.falling || b.falling) continue;
        this._resolvePenCollision(a, b);
      }
    }

    // Impact particles
    this.particles.forEach((pt) => {
      pt.x += pt.vx * dt; pt.y += pt.vy * dt;
      pt.life -= 0.04 * dt; pt.vy += 0.08 * dt;
    });
    this.particles = this.particles.filter((pt) => pt.life > 0);
  }

  _isPastEdge(p) {
    const b = this.bench;
    const half = this.PEN_LENGTH / 2 - PHYSICS.EDGE_MARGIN;
    return (
      p.x < b.x - half || p.x > b.x + b.w + half ||
      p.y < b.y - half || p.y > b.y + b.h + half
    );
  }

  _resolvePenCollision(a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const dist = Math.hypot(dx, dy) || 0.001;
    const minDist = this.PEN_LENGTH * 0.42;
    if (dist >= minDist) return;

    const nx = dx / dist, ny = dy / dist;
    const overlap = minDist - dist;
    const totalMass = a.mass + b.mass;
    a.x -= nx * overlap * (b.mass / totalMass);
    a.y -= ny * overlap * (a.mass / totalMass);
    b.x += nx * overlap * (a.mass / totalMass);
    b.y += ny * overlap * (a.mass / totalMass);

    const rvx = b.vx - a.vx, rvy = b.vy - a.vy;
    const velAlongNormal = rvx * nx + rvy * ny;
    if (velAlongNormal > 0) return;

    const impulse = (-(1 + PHYSICS.RESTITUTION) * velAlongNormal) / (1 / a.mass + 1 / b.mass);
    const ix = impulse * nx * PHYSICS.KNOCKBACK_SCALE, iy = impulse * ny * PHYSICS.KNOCKBACK_SCALE;

    a.vx -= ix / a.mass; a.vy -= iy / a.mass;
    b.vx += ix / b.mass; b.vy += iy / b.mass;
    a.angularVel += (Math.random() - 0.5) * 0.06;
    b.angularVel += (Math.random() - 0.5) * 0.06;

    this.settledPending.add(a.id);
    this.settledPending.add(b.id);

    const strength = Math.min(1, Math.abs(velAlongNormal) / 60);
    this._spawnImpact((a.x + b.x) / 2, (a.y + b.y) / 2, strength);
    this.onCollision(a.id, b.id, strength);
  }

  _resolveBumperCollisions(p) {
    if (!p.alive || p.falling) return;
    const pr = 10;

    for (const bmp of this.bumpers) {
      let nx = 0, ny = 0, dist = 0, overlap = 0;

      if (bmp.isCircle) {
        const dx = p.x - bmp.x, dy = p.y - bmp.y;
        dist = Math.hypot(dx, dy) || 0.001;
        const minDist = bmp.w / 2 + pr;
        if (dist >= minDist) continue;
        nx = dx / dist; ny = dy / dist;
        overlap = minDist - dist;
      } else {
        const cx = bmp.x + bmp.w / 2, cy = bmp.y + bmp.h / 2;
        const closestX = Math.max(bmp.x, Math.min(bmp.x + bmp.w, p.x));
        const closestY = Math.max(bmp.y, Math.min(bmp.y + bmp.h, p.y));
        const dx = p.x - closestX, dy = p.y - closestY;
        dist = Math.hypot(dx, dy);

        if (dist >= pr && (p.x >= bmp.x && p.x <= bmp.x + bmp.w && p.y >= bmp.y && p.y <= bmp.y + bmp.h) === false) {
          continue;
        }

        if (dist > 0.001) {
          nx = dx / dist; ny = dy / dist;
          overlap = pr - dist;
        } else {
          nx = p.x > cx ? 1 : -1; ny = 0;
          overlap = pr;
        }
      }

      p.x += nx * overlap;
      p.y += ny * overlap;

      const velAlongNormal = p.vx * nx + p.vy * ny;
      if (velAlongNormal < 0) {
        p.vx -= (1 + PHYSICS.BUMPER_RESTITUTION) * velAlongNormal * nx;
        p.vy -= (1 + PHYSICS.BUMPER_RESTITUTION) * velAlongNormal * ny;
        p.angularVel += (Math.random() - 0.5) * 0.08;

        const strength = Math.min(1, Math.abs(velAlongNormal) / 50);
        this._spawnImpact(p.x, p.y, strength);
        this.onBumperHit(bmp, strength);
      }
    }
  }

  _spawnImpact(x, y, strength) {
    const count = 3 + Math.round(strength * 8);
    for (let i = 0; i < count; i++) {
      const ang = Math.random() * Math.PI * 2;
      const spd = 1.0 + Math.random() * 3 * (0.4 + strength);
      this.particles.push({
        x, y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd,
        life: 1, color: Math.random() > 0.5 ? "#facc15" : "#38bdf8",
      });
    }
  }

  screenShake(strength = 6) {
    const canvas = this.canvas;
    const original = canvas.style.transform;
    let t = 0;
    const shake = () => {
      t += 1;
      if (t > 10) { canvas.style.transform = original; return; }
      const dx = (Math.random() - 0.5) * strength * (1 - t / 10);
      const dy = (Math.random() - 0.5) * strength * (1 - t / 10);
      canvas.style.transform = `translate(${dx}px, ${dy}px)`;
      requestAnimationFrame(shake);
    };
    shake();
  }

  anyPenMoving() {
    return Object.values(this.pens).some(
      (p) => p.alive && !p.falling && (Math.hypot(p.vx, p.vy) > PHYSICS.MIN_SPEED || this.settledPending.has(p.id))
    );
  }

  // ---------------------------------------------------------------- render

  _render() {
    const ctx = this.ctx, b = this.bench, W = this.canvas.width, H = this.canvas.height;
    ctx.clearRect(0, 0, W, H);

    // 1. Ambient Floor Margin Outer Backdrop
    ctx.fillStyle = "#0a0d14";
    ctx.fillRect(0, 0, W, H);

    // 2. Authoritative Tabletop Surface (Occupies ~94% of canvas area!)
    ctx.save();

    // Tabletop Floor Drop Shadow
    ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
    this._roundRect(ctx, b.x + 6, b.y + 10, b.w, b.h + 8, 16);
    ctx.fill();

    // Tabletop 3D Front Lip
    ctx.fillStyle = this.benchColorDark || "#381e0b";
    this._roundRect(ctx, b.x, b.y + 6, b.w, b.h + 6, 16);
    ctx.fill();

    // Tabletop Surface Wood Gradient
    const grad = ctx.createLinearGradient(b.x, b.y, b.x, b.y + b.h);
    grad.addColorStop(0, this.benchColorLight || "#784f29");
    grad.addColorStop(1, this.benchColorDark || "#422812");
    ctx.fillStyle = grad;
    this._roundRect(ctx, b.x, b.y, b.w, b.h, 16);
    ctx.fill();

    // Subtle Wood Grain Curves & Scratches
    ctx.globalAlpha = 0.08;
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 2;
    for (let i = 0; i < 11; i++) {
      ctx.beginPath();
      const yPos = b.y + 16 + (i * (b.h - 32)) / 10;
      ctx.moveTo(b.x + 12, yPos);
      ctx.bezierCurveTo(b.x + b.w * 0.3, yPos + (i % 2 === 0 ? 8 : -8), b.x + b.w * 0.7, yPos + (i % 2 === 0 ? -8 : 8), b.x + b.w - 12, yPos);
      ctx.stroke();
    }
    ctx.restore();

    // Tabletop Edge Bevel Highlight
    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 2;
    this._roundRect(ctx, b.x, b.y, b.w, b.h, 16);
    ctx.stroke();
    ctx.restore();

    // 3. Render Bumpers
    this.bumpers.forEach((bmp) => this._drawBumper(bmp));

    // 4. Dynamic Pen Shadows & Pen Bodies
    for (const id in this.pens) {
      const p = this.pens[id];
      if (p.alive) this._drawPenShadow(p);
    }
    for (const id in this.pens) {
      const p = this.pens[id];
      this._drawTrail(p);
    }
    for (const id in this.pens) {
      const p = this.pens[id];
      if (p.alive) this._drawPen(p);
    }

    // 5. Impact Particles
    this.particles.forEach((pt) => {
      ctx.globalAlpha = Math.max(0, pt.life);
      ctx.fillStyle = pt.color;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 3.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    // 6. Debug Telemetry Overlay
    if (this.debugMode) {
      this._renderDebugOverlay(ctx);
    }
  }

  _drawBumper(bmp) {
    const ctx = this.ctx;
    ctx.save();
    ctx.translate(bmp.x + bmp.w / 2, bmp.y + bmp.h / 2);
    ctx.rotate(bmp.angle || 0);

    ctx.shadowColor = "rgba(0, 0, 0, 0.4)";
    ctx.shadowBlur = 8;
    ctx.shadowOffsetY = 4;

    if (bmp.type === "wood") {
      ctx.fillStyle = "#8d5b32"; ctx.strokeStyle = "#4d2e14"; ctx.lineWidth = 2;
      this._roundRect(ctx, -bmp.w / 2, -bmp.h / 2, bmp.w, bmp.h, 6); ctx.fill(); ctx.stroke();
    } else if (bmp.type === "rubber") {
      ctx.fillStyle = "#ec4899"; ctx.strokeStyle = "#9d174d"; ctx.lineWidth = 2;
      this._roundRect(ctx, -bmp.w / 2, -bmp.h / 2, bmp.w, bmp.h, 6); ctx.fill(); ctx.stroke();
    } else if (bmp.type === "metal") {
      ctx.fillStyle = "#94a3b8"; ctx.strokeStyle = "#475569"; ctx.lineWidth = 2;
      this._roundRect(ctx, -bmp.w / 2, -bmp.h / 2, bmp.w, bmp.h, 4); ctx.fill(); ctx.stroke();
    } else {
      ctx.fillStyle = "#38bdf8"; ctx.strokeStyle = "#0284c7"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(0, 0, bmp.w / 2, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    ctx.restore();
  }

  _drawPenShadow(p) {
    const ctx = this.ctx;
    const alpha = p.falling ? Math.max(0, 0.35 - p.fallProgress * 0.3) : 0.35;
    const offsetY = p.falling ? 10 + p.fallProgress * 25 : 8;
    const scaleX = p.falling ? Math.max(0.2, 1 - p.fallProgress * 0.5) : 1;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(p.x, p.y + offsetY);
    ctx.rotate(p.angle);
    ctx.scale(scaleX, 0.4);

    ctx.fillStyle = "#000000";
    ctx.beginPath();
    ctx.arc(0, 0, this.PEN_LENGTH * 0.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  _drawTrail(p) {
    const ctx = this.ctx;
    p.trail.forEach((t) => {
      ctx.globalAlpha = Math.max(0, t.life * 0.35);
      ctx.fillStyle = p.trailColor;
      ctx.beginPath(); ctx.arc(t.x, t.y, 4.5, 0, Math.PI * 2); ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  _drawPen(p) {
    const ctx = this.ctx;
    const alpha = p.falling ? Math.max(0, 1 - p.fallProgress / 1.5) : 1;
    const scale = p.falling ? Math.max(0.2, 1 - p.fallProgress * 0.5) : 1;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(p.x, p.y);
    ctx.rotate(p.angle);

    if (window.PenVisuals) {
      window.PenVisuals.drawPenToCanvas(ctx, p.assetKey || "classic-blue", 0, 0, 0, scale);
    } else {
      if (p.glow) { ctx.shadowColor = p.color; ctx.shadowBlur = 22; }
      const L = this.PEN_LENGTH, Wd = this.PEN_WIDTH;
      ctx.fillStyle = p.color;
      this._roundRect(ctx, -L / 2, -Wd / 2, L, Wd, Wd / 2);
      ctx.fill();
    }

    ctx.restore();
  }

  _renderDebugOverlay(ctx) {
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.88)";
    ctx.strokeStyle = "rgba(139, 92, 246, 0.6)";
    ctx.lineWidth = 1;
    ctx.fillRect(10, 10, 380, 115);
    ctx.strokeRect(10, 10, 380, 115);

    ctx.fillStyle = "#34d399";
    ctx.font = "11px monospace";
    ctx.fillText("=== PENFIGHT DEBUG TELEMETRY (D) ===", 18, 26);

    const pens = Object.values(this.pens);
    pens.forEach((p, idx) => {
      const spd = Math.hypot(p.vx, p.vy).toFixed(2);
      const edgeDist = Math.min(
        p.x - this.bench.x, (this.bench.x + this.bench.w) - p.x,
        p.y - this.bench.y, (this.bench.y + this.bench.h) - p.y
      ).toFixed(0);
      ctx.fillStyle = p.color || "#ffffff";
      ctx.fillText(`P${idx + 1} (${p.id}): MASS=${p.mass.toFixed(1)} | VEL=${spd} | POS=(${p.x.toFixed(0)},${p.y.toFixed(0)}) | EDGE=${edgeDist}px`, 18, 46 + idx * 20);
    });

    ctx.fillStyle = "#facc15";
    ctx.fillText(`TABLEBOUNDS: ${this.bench.w}x${this.bench.h} | BUMPERS: ${this.bumpers.length} | MOVING: ${this.anyPenMoving()}`, 18, 104);
    ctx.restore();
  }

  _roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
}
