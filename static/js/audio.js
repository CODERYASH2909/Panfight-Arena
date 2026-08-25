/* =========================================================================
   PENFIGHT ARENA — Audio
   Small synthesized SFX via the WebAudio API, so the game has real
   game-feel audio without shipping binary asset files. Respects the
   Music/SFX toggles stored in localStorage-free session state (settings
   are per-battle-session; a persisted user preference is a natural
   follow-up — see README "Known scaffolding").
   ========================================================================= */

class PenFightAudio {
  constructor() {
    this.ctx = null;
    this.sfxOn = true;
  }

  _ensureCtx() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AC();
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }

  setSfx(on) { this.sfxOn = on; }

  _tone(freq, duration, type = "sine", gain = 0.18, glideTo = null) {
    if (!this.sfxOn) return;
    const ctx = this._ensureCtx();
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, ctx.currentTime + duration);
    g.gain.setValueAtTime(gain, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(g).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  }

  _noise(duration, gain = 0.15) {
    if (!this.sfxOn) return;
    const ctx = this._ensureCtx();
    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    const g = ctx.createGain();
    g.gain.setValueAtTime(gain, ctx.currentTime);
    src.connect(g).connect(ctx.destination);
    src.start();
  }

  click() { this._tone(600, 0.05, "square", 0.08); }
  flick() { this._tone(340, 0.16, "sawtooth", 0.16, 120); }
  collision(strength = 0.6) { this._noise(0.12, 0.12 + strength * 0.2); this._tone(180, 0.08, "square", 0.1); }
  bumperHit(type = "wood", strength = 0.6) {
    if (!this.sfxOn) return;
    if (type === "metal") {
      this._tone(1200, 0.08, "sine", 0.15 + strength * 0.1, 400);
    } else if (type === "rubber") {
      this._tone(220, 0.12, "triangle", 0.2 + strength * 0.15, 90);
    } else {
      this._noise(0.08, 0.1 + strength * 0.15);
      this._tone(320, 0.07, "square", 0.12, 140);
    }
  }
  fall() { this._tone(500, 0.5, "sine", 0.15, 60); this._noise(0.4, 0.08); }
  countdownTick() { this._tone(440, 0.12, "sine", 0.15); }
  fight() { this._tone(880, 0.25, "square", 0.2, 660); }
  victory() {
    [523, 659, 784, 1046].forEach((f, i) => setTimeout(() => this._tone(f, 0.3, "triangle", 0.18), i * 110));
  }
  defeat() {
    [400, 340, 260].forEach((f, i) => setTimeout(() => this._tone(f, 0.35, "sawtooth", 0.14), i * 140));
  }
}

const pfAudio = new PenFightAudio();
