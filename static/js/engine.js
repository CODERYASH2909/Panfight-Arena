/* =========================================================================
   PENFIGHT ARENA — Physics Engine
   A small top-down arcade physics engine: pens are capsules on a bench,
   flicked with direction + power, sliding with friction, colliding with
   momentum transfer, and falling off the bench edge when knocked past it.
   Framework-free so it can run identically in local hotseat play and in
   the online battle screen (which additionally syncs settled states over
   a WebSocket — see battle_online.js).
   ========================================================================= */

class PenFightEngine {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Object} opts
   *   bench: {x,y,w,h} - bench playfield rectangle in canvas coords
   *   onSettle: fn({penId, x, y, angle}) called once a flicked pen fully stops
   *   onFall: fn(penId) called the instant a pen goes over the bench edge
   *   onCollision: fn(penIdA, penIdB, strength) called on impact
   */
  constructor(canvas, opts) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.bench = opts.bench;
    this.onSettle = opts.onSettle || (() => {});
    this.onFall = opts.onFall || (() => {});
    this.onCollision = opts.onCollision || (() => {});
    this.pens = {};              // id -> pen state
    this.particles = [];         // impact / trail particles
    this.running = false;
    this.settledPending = new Set(); // pens we're waiting to report as settled
    this._loop = this._loop.bind(this);

    // Visual constants
    this.PEN_LENGTH = 74;
    this.PEN_WIDTH = 15;
    this.FRICTION = 0.985;       // linear velocity damping per frame @60fps
    this.ANGULAR_FRICTION = 0.94;
    this.MIN_SPEED = 4;          // px/s below which a pen is considered stopped
    this.RESTITUTION = 0.72;     // bounce factor on collision
    this.EDGE_MARGIN = 6;        // how far past bench edge counts as "fallen"
  }

  addPen(id, { x, y, angle = 0, color = "#3b82f6", accent = "#93c5fd", trailColor = "#60a5fa", glow = false, mass = 1, friction = 1, icon = "" }) {
    this.pens[id] = {
      id, x, y, angle,
      vx: 0, vy: 0, angularVel: 0,
      mass, frictionMult: friction,
      color, accent, trailColor, glow, icon,
      alive: true, falling: false, fallProgress: 0,
      trail: [],
    };
  }

  removePen(id) { delete this.pens[id]; }

  /** Apply a flick impulse to a pen. angleRad is world-space direction, power 0..1 */
  flick(id, angleRad, power) {
    const pen = this.pens[id];
    if (!pen || !pen.alive) return;
    const MAX_SPEED = 780;
    const speed = 140 + power * MAX_SPEED;
    pen.vx = Math.cos(angleRad) * speed;
    pen.vy = Math.sin(angleRad) * speed;
    pen.angularVel = (Math.random() - 0.5) * 0.12 * power;
    this.settledPending.add(id);
  }

  /** Force-set a pen's transform (used to sync authoritative state from the network peer) */
  setState(id, { x, y, angle, vx = 0, vy = 0 }) {
    const pen = this.pens[id];
    if (!pen) return;
    pen.x = x; pen.y = y; pen.angle = angle; pen.vx = vx; pen.vy = vy;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this._lastTs = performance.now();
    requestAnimationFrame(this._loop);
  }

  stop() { this.running = false; }

  _loop(ts) {
    if (!this.running) return;
    const dt = Math.min(32, ts - this._lastTs) / 16.6667; // normalize to ~60fps steps
    this._lastTs = ts;
    this._update(dt);
    this._render();
    requestAnimationFrame(this._loop);
  }

  _update(dt) {
    const ids = Object.keys(this.pens);

    // -- integrate motion --------------------------------------------
    for (const id of ids) {
      const p = this.pens[id];
      if (!p.alive) continue;

      if (p.falling) {
        p.fallProgress += 0.035 * dt;
        p.y += 2.2 * dt * p.fallProgress;
        p.angle += 0.09 * dt;
        p.x += p.fallVX * dt * 0.4;
        if (p.fallProgress >= 1.4) {
          p.alive = false;
          this.onFall(id);
        }
        continue;
      }

      const speed = Math.hypot(p.vx, p.vy);
      if (speed > 0.05) {
        if (speed > 260 && Math.random() < 0.6) {
          p.trail.push({ x: p.x, y: p.y, life: 1 });
        }
        p.x += p.vx * dt * 0.1667;
        p.y += p.vy * dt * 0.1667;
        p.angle += p.angularVel * dt;

        const fr = Math.pow(this.FRICTION / p.frictionMult, dt);
        p.vx *= fr; p.vy *= fr;
        p.angularVel *= Math.pow(this.ANGULAR_FRICTION, dt);

        if (Math.hypot(p.vx, p.vy) < this.MIN_SPEED) {
          p.vx = 0; p.vy = 0; p.angularVel = 0;
          if (this.settledPending.has(id)) {
            this.settledPending.delete(id);
            this.onSettle({ penId: id, x: p.x, y: p.y, angle: p.angle });
          }
        }
      }

      // fade trail
      p.trail.forEach((t) => (t.life -= 0.03 * dt));
      p.trail = p.trail.filter((t) => t.life > 0);

      // -- bench-edge check --
      if (this._isPastEdge(p)) {
        p.falling = true;
        p.fallVX = p.vx * 0.3;
      }
    }

    // -- pairwise collision ------------------------------------------
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = this.pens[ids[i]], b = this.pens[ids[j]];
        if (!a.alive || !b.alive || a.falling || b.falling) continue;
        this._resolveCollision(a, b);
      }
    }

    // -- particles --
    this.particles.forEach((pt) => { pt.x += pt.vx * dt; pt.y += pt.vy * dt; pt.life -= 0.04 * dt; pt.vy += 0.15 * dt; });
    this.particles = this.particles.filter((pt) => pt.life > 0);
  }

  _isPastEdge(p) {
    const b = this.bench;
    const half = this.PEN_LENGTH / 2 - this.EDGE_MARGIN;
    return (
      p.x < b.x - half || p.x > b.x + b.w + half ||
      p.y < b.y - half || p.y > b.y + b.h + half
    );
  }

  _resolveCollision(a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const dist = Math.hypot(dx, dy) || 0.001;
    const minDist = this.PEN_LENGTH * 0.42;
    if (dist >= minDist) return;

    const nx = dx / dist, ny = dy / dist;
    const overlap = minDist - dist;
    const totalMass = a.mass + b.mass;
    a.x -= nx * overlap * (b.mass / totalMass);
    a.y -= ny * overlap * (b.mass / totalMass);
    b.x += nx * overlap * (a.mass / totalMass);
    b.y += ny * overlap * (a.mass / totalMass);

    const rvx = b.vx - a.vx, rvy = b.vy - a.vy;
    const velAlongNormal = rvx * nx + rvy * ny;
    if (velAlongNormal > 0) return; // separating already

    const restitution = this.RESTITUTION;
    const impulse = (-(1 + restitution) * velAlongNormal) / (1 / a.mass + 1 / b.mass);
    const ix = impulse * nx, iy = impulse * ny;

    a.vx -= ix / a.mass; a.vy -= iy / a.mass;
    b.vx += ix / b.mass; b.vy += iy / b.mass;
    a.angularVel += (Math.random() - 0.5) * 0.15;
    b.angularVel += (Math.random() - 0.5) * 0.15;

    this.settledPending.add(a.id);
    this.settledPending.add(b.id);

    const strength = Math.min(1, Math.abs(velAlongNormal) / 500);
    this._spawnImpact((a.x + b.x) / 2, (a.y + b.y) / 2, strength);
    this.onCollision(a.id, b.id, strength);
  }

  _spawnImpact(x, y, strength) {
    const count = 6 + Math.round(strength * 14);
    for (let i = 0; i < count; i++) {
      const ang = Math.random() * Math.PI * 2;
      const spd = 2 + Math.random() * 6 * (0.4 + strength);
      this.particles.push({
        x, y, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd,
        life: 1, color: Math.random() > 0.5 ? "#facc15" : "#f97316",
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
      (p) => p.alive && !p.falling && (Math.hypot(p.vx, p.vy) > this.MIN_SPEED || this.settledPending.has(p.id))
    );
  }

  // ---------------------------------------------------------------- render

  _render() {
    const ctx = this.ctx, b = this.bench, W = this.canvas.width, H = this.canvas.height;
    ctx.clearRect(0, 0, W, H);

    // bench surface
    const grad = ctx.createLinearGradient(0, b.y, 0, b.y + b.h);
    grad.addColorStop(0, this.benchColorLight || "#a97c50");
    grad.addColorStop(1, this.benchColorDark || "#6b4226");
    ctx.fillStyle = grad;
    this._roundRect(ctx, b.x, b.y, b.w, b.h, 18);
    ctx.fill();

    // wood grain lines
    ctx.save();
    ctx.globalAlpha = 0.08;
    ctx.strokeStyle = "#000";
    for (let i = 0; i < 7; i++) {
      ctx.beginPath();
      ctx.moveTo(b.x + 10, b.y + 10 + (i * (b.h - 20)) / 6);
      ctx.lineTo(b.x + b.w - 10, b.y + 14 + (i * (b.h - 20)) / 6);
      ctx.stroke();
    }
    ctx.restore();

    // edge glow
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.15)";
    ctx.lineWidth = 2;
    this._roundRect(ctx, b.x, b.y, b.w, b.h, 18);
    ctx.stroke();
    ctx.restore();

    // pens
    for (const id in this.pens) {
      const p = this.pens[id];
      this._drawTrail(p);
    }
    for (const id in this.pens) {
      const p = this.pens[id];
      if (p.alive) this._drawPen(p);
    }

    // particles
    this.particles.forEach((pt) => {
      ctx.globalAlpha = Math.max(0, pt.life);
      ctx.fillStyle = pt.color;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    });
  }

  _drawTrail(p) {
    const ctx = this.ctx;
    p.trail.forEach((t) => {
      ctx.globalAlpha = Math.max(0, t.life * 0.4);
      ctx.fillStyle = p.trailColor;
      ctx.beginPath();
      ctx.arc(t.x, t.y, 5, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  _drawPen(p) {
    const ctx = this.ctx;
    const alpha = p.falling ? Math.max(0, 1 - p.fallProgress / 1.4) : 1;
    const scale = p.falling ? Math.max(0.3, 1 - p.fallProgress * 0.5) : 1;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(p.x, p.y);
    ctx.rotate(p.angle);
    ctx.scale(scale, scale);

    if (p.glow) {
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 22;
    }

    const L = this.PEN_LENGTH, Wd = this.PEN_WIDTH;

    // body
    const bodyGrad = ctx.createLinearGradient(-L / 2, 0, L / 2, 0);
    bodyGrad.addColorStop(0, p.accent);
    bodyGrad.addColorStop(1, p.color);
    ctx.fillStyle = bodyGrad;
    this._roundRect(ctx, -L / 2, -Wd / 2, L * 0.78, Wd, Wd / 2);
    ctx.fill();

    // cap / tip
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.moveTo(L * 0.28, -Wd / 2);
    ctx.lineTo(L / 2, 0);
    ctx.lineTo(L * 0.28, Wd / 2);
    ctx.closePath();
    ctx.fill();

    // grip
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.fillRect(-L * 0.1, -Wd / 2, L * 0.18, Wd);

    // clip
    ctx.fillStyle = "rgba(255,255,255,0.6)";
    ctx.fillRect(-L / 2 + 4, -Wd / 2 - 3, 3, Wd * 0.6);

    ctx.shadowBlur = 0;
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
