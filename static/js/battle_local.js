/* PenFight Arena — Local Battle Controller (Best-of-3 System) */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const config = JSON.parse(sessionStorage.getItem("pf_local_config") || "null") || {
    player1: { name: "Player 1", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#3b82f6", accent: "#93c5fd", trail: "#60a5fa", glow: false } },
    player2: { name: "Player 2", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#f87171", accent: "#fecaca", trail: "#fca5a5", glow: false } },
  };

  document.getElementById("hud-p1-name").textContent = config.player1.name;
  document.getElementById("hud-p2-name").textContent = config.player2.name;

  canvas.width = 960;
  canvas.height = 520;
  canvas.style.background = `linear-gradient(135deg, ${window.PF_ARENA.fromColor}, ${window.PF_ARENA.toColor})`;

  const engine = new PenFightEngine(canvas, {
    onSettle: handleSettle,
    onFall: handleFall,
    onCollision: (a, b, strength) => {
      pfAudio.collision(strength);
      engine.screenShake(4 + strength * 10);
    },
    onBumperHit: (bmp, strength) => {
      pfAudio.bumperHit(bmp.type, strength);
      engine.screenShake(2 + strength * 6);
    },
  });
  engine.benchColorLight = shade(window.PF_ARENA.benchColor, 24);
  engine.benchColorDark = shade(window.PF_ARENA.benchColor, -30);

  // Authoritative tabletop bounds (occupying ~94% of canvas area)
  const bench = engine.bench;

  const penOwner = { p1: "player1", p2: "player2" };
  const penPowerStat = { p1: config.player1.pen.power || 1, p2: config.player2.pen.power || 1 };

  // Best-of-3 Match State Machine
  let currentRound = 1;
  let p1RoundWins = 0;
  let p2RoundWins = 0;

  let currentTurn = "p1";
  let roundOver = false;
  let matchOver = false;
  let isTransitioningRound = false;
  let waitingForSettle = false;
  let dragging = null;

  const turnBanner = document.getElementById("turn-banner");
  const roundBanner = document.getElementById("round-banner");
  const powerFill = document.getElementById("power-fill");
  const powerLabel = document.getElementById("power-label");
  const p1WinsDot = document.getElementById("p1-wins-dots");
  const p2WinsDot = document.getElementById("p2-wins-dots");
  const MAX_PULL = 95;

  function updateScoreHUD() {
    p1WinsDot.textContent = "●".repeat(p1RoundWins) + "○".repeat(2 - p1RoundWins);
    p2WinsDot.textContent = "●".repeat(p2RoundWins) + "○".repeat(2 - p2RoundWins);
    if (p1RoundWins === 1 && p2RoundWins === 1) {
      roundBanner.textContent = "FINAL ROUND (1 — 1)";
      roundBanner.style.color = "var(--gold)";
    } else {
      roundBanner.textContent = `ROUND ${currentRound}`;
      roundBanner.style.color = "var(--text-secondary)";
    }
  }

  function setupRound() {
    engine.reset();
    roundOver = false;
    isTransitioningRound = false;
    waitingForSettle = false;
    dragging = null;
    currentTurn = (currentRound % 2 === 1) ? "p1" : "p2";

    // Pens start 15% and 85% from left edge of 912px table (~638px distance apart)
    engine.addPen("p1", {
      x: bench.x + bench.w * 0.15, y: bench.y + bench.h / 2, angle: 0,
      color: config.player1.skin.color, accent: config.player1.skin.accent,
      trailColor: config.player1.skin.trail, glow: !!config.player1.skin.glow,
      mass: config.player1.pen.mass || 1, friction: config.player1.pen.friction || 1,
      assetKey: config.player1.skin.assetKey || "classic-blue"
    });
    engine.addPen("p2", {
      x: bench.x + bench.w * 0.85, y: bench.y + bench.h / 2, angle: Math.PI,
      color: config.player2.skin.color, accent: config.player2.skin.accent,
      trailColor: config.player2.skin.trail, glow: !!config.player2.skin.glow,
      mass: config.player2.pen.mass || 1, friction: config.player2.pen.friction || 1,
      assetKey: config.player2.skin.assetKey || "sunset-blaze"
    });

    // Generate fresh procedural bumpers for round
    engine.generateBumpers(`local_r${currentRound}_${Date.now()}`);
    updateScoreHUD();
    updateTurnUI();
  }

  function updateTurnUI() {
    document.getElementById("hud-p1").classList.toggle("active-turn", currentTurn === "p1");
    document.getElementById("hud-p2").classList.toggle("active-turn", currentTurn === "p2");
    const name = currentTurn === "p1" ? config.player1.name : config.player2.name;
    turnBanner.textContent = `${name.toUpperCase()}'S TURN`;
  }

  // ---------------------------------------------------------------- aiming

  function canvasPos(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width, scaleY = canvas.height / rect.height;
    const clientX = evt.touches ? evt.touches[0].clientX : evt.clientX;
    const clientY = evt.touches ? evt.touches[0].clientY : evt.clientY;
    return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
  }

  function startDrag(evt) {
    if (matchOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving()) return;
    const pos = canvasPos(evt);
    const pen = engine.pens[currentTurn];
    if (!pen) return;
    const dist = Math.hypot(pos.x - pen.x, pos.y - pen.y);
    if (dist > 75) return;
    dragging = { penId: currentTurn, anchorX: pen.x, anchorY: pen.y, mouseX: pos.x, mouseY: pos.y };
    pfAudio.click();
  }

  function moveDrag(evt) {
    if (!dragging) return;
    const pos = canvasPos(evt);
    dragging.mouseX = pos.x; dragging.mouseY = pos.y;
    const dx = dragging.mouseX - dragging.anchorX, dy = dragging.mouseY - dragging.anchorY;
    const pull = Math.min(MAX_PULL, Math.hypot(dx, dy));
    const power = pull / MAX_PULL;
    powerFill.style.width = `${power * 100}%`;
    powerLabel.textContent = power < 0.34 ? "LOW" : power < 0.7 ? "MEDIUM" : "HIGH";
  }

  function endDrag() {
    if (!dragging) return;
    const dx = dragging.mouseX - dragging.anchorX, dy = dragging.mouseY - dragging.anchorY;
    const pull = Math.min(MAX_PULL, Math.hypot(dx, dy));
    const power = pull / MAX_PULL;
    if (power > 0.08) {
      const angle = Math.atan2(-dy, -dx);
      engine.flick(dragging.penId, angle, power * (penPowerStat[dragging.penId] || 1));
      pfAudio.flick();
      waitingForSettle = true;
    }
    dragging = null;
    powerFill.style.width = "0%";
    powerLabel.textContent = "LOW";
  }

  canvas.addEventListener("mousedown", startDrag);
  canvas.addEventListener("mousemove", moveDrag);
  window.addEventListener("mouseup", endDrag);
  canvas.addEventListener("touchstart", (e) => { startDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchmove", (e) => { moveDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchend", endDrag);

  function drawAimOverlay() {
    if (dragging) {
      const ctx = canvas.getContext("2d");
      const { anchorX, anchorY, mouseX, mouseY } = dragging;
      ctx.save();
      ctx.strokeStyle = "rgba(250, 204, 21, 0.85)";
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 6]);
      ctx.beginPath(); ctx.moveTo(anchorX, anchorY); ctx.lineTo(mouseX, mouseY); ctx.stroke();
      const fx = anchorX - (mouseX - anchorX), fy = anchorY - (mouseY - anchorY);
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(52, 211, 153, 0.9)";
      ctx.beginPath(); ctx.moveTo(anchorX, anchorY); ctx.lineTo(fx, fy); ctx.stroke();
      ctx.restore();
    }
    requestAnimationFrame(drawAimOverlay);
  }

  // ---------------------------------------------------------------- turns & round logic

  function handleSettle() {
    if (matchOver || roundOver || isTransitioningRound) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();
    }
  }

  setInterval(() => {
    if (!matchOver && !roundOver && !isTransitioningRound && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();
    }
  }, 200);

  function handleFall(penId) {
    if (roundOver || matchOver || isTransitioningRound) return;
    roundOver = true;
    isTransitioningRound = true;
    pfAudio.fall();
    engine.screenShake(14);

    const loserSlot = penOwner[penId];
    const winnerSlot = loserSlot === "player1" ? "player2" : "player1";
    if (winnerSlot === "player1") p1RoundWins++; else p2RoundWins++;
    updateScoreHUD();

    const winnerName = winnerSlot === "player1" ? config.player1.name : config.player2.name;

    // First to 2 round wins claims MATCH VICTORY!
    if (p1RoundWins >= 2 || p2RoundWins >= 2) {
      matchOver = true;
      showVictory(winnerSlot);
    } else {
      // 2.5s Round Result Toast, then transition to Round 2 or Round 3!
      showRoundToast(winnerName, currentRound, p1RoundWins, p2RoundWins, () => {
        currentRound++;
        isTransitioningRound = false;
        setupRound();
        runCountdown();
      });
    }
  }

  function showRoundToast(winnerName, roundNum, score1, score2, onComplete) {
    const toast = document.createElement("div");
    toast.className = "pf-overlay";
    const isFinalNext = (score1 === 1 && score2 === 1);
    toast.innerHTML = `
      <div class="pf-center">
        <div class="pf-faint" style="letter-spacing:0.18em; font-size:14px; text-transform:uppercase;">ROUND ${roundNum} RESULT</div>
        <div style="font-family:var(--font-display); font-size:52px; font-weight:900; color:var(--gold); margin-top:8px;">${winnerName.toUpperCase()} WINS ROUND ${roundNum}</div>
        <div style="font-family:var(--font-display); font-size:32px; font-weight:800; margin-top:12px; color:white;">
          ${score1}  —  ${score2}
        </div>
        ${isFinalNext ? `<div class="pf-badge pf-badge-mythic" style="margin-top:16px; font-size:14px; padding:6px 16px;">🔥 FINAL ROUND NEXT!</div>` : ""}
        <div class="pf-muted pf-mt-24" style="font-size:13px;">Preparing next round...</div>
      </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      document.body.removeChild(toast);
      onComplete();
    }, 2500);
  }

  // ---------------------------------------------------------------- flow

  function shade(hex, percent) {
    try {
      const n = parseInt(hex.replace("#", ""), 16);
      let r = (n >> 16) + percent, g = ((n >> 8) & 0xff) + percent, b = (n & 0xff) + percent;
      r = Math.max(0, Math.min(255, r)); g = Math.max(0, Math.min(255, g)); b = Math.max(0, Math.min(255, b));
      return `rgb(${r},${g},${b})`;
    } catch (e) { return hex; }
  }

  function runCountdown() {
    const overlay = document.getElementById("countdown-overlay");
    const text = document.getElementById("countdown-text");
    overlay.style.display = "flex";
    const seq = ["3", "2", "1", "FIGHT!"];
    let i = 0;
    const step = () => {
      text.textContent = seq[i];
      if (seq[i] === "FIGHT!") { pfAudio.fight(); text.style.color = "#34d399"; }
      else { pfAudio.countdownTick(); }
      i++;
      if (i < seq.length) {
        setTimeout(step, 600);
      } else {
        setTimeout(() => {
          overlay.style.display = "none";
          text.style.color = "#ffffff";
          if (!engine.running) {
            engine.start();
            drawAimOverlay();
          }
          updateTurnUI();
        }, 400);
      }
    };
    step();
  }

  function showVictory(winnerSlot) {
    const name = winnerSlot === "player1" ? config.player1.name : config.player2.name;
    document.getElementById("victory-winner").textContent = `${name.toUpperCase()} WINS MATCH (${p1RoundWins} - ${p2RoundWins})`;
    if (winnerSlot === "player1") pfAudio.victory(); else pfAudio.defeat();

    fetch(window.PF_LOCAL_RESULT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": window.PF_CSRF },
      body: JSON.stringify({ winner: winnerSlot }),
    })
      .then((r) => r.json())
      .then((data) => {
        const rewards = data.rewards || {};
        const box = document.getElementById("victory-rewards");
        box.innerHTML = `
          <div class="pf-badge pf-badge-legendary">🪙 +${rewards.pp || 0} PP</div>
          <div class="pf-badge pf-badge-rare">⭐ +${rewards.xp || 0} XP</div>
          ${rewards.streak_bonus ? `<div class="pf-badge pf-badge-epic">🔥 +${rewards.streak_bonus} Streak Bonus</div>` : ""}
        `;
        (data.achievements || []).forEach((a) => {
          const div = document.createElement("div");
          div.className = "pf-badge pf-badge-mythic";
          div.textContent = `${a.icon} ${a.name}`;
          box.appendChild(div);
        });
      })
      .catch(() => {});

    setTimeout(() => {
      document.getElementById("victory-overlay").style.display = "flex";
    }, 400);
  }

  document.getElementById("rematch-btn").addEventListener("click", () => window.location.reload());

  const sfxToggle = document.getElementById("sfx-toggle");
  sfxToggle.addEventListener("click", () => {
    pfAudio.setSfx(!pfAudio.sfxOn);
    sfxToggle.textContent = pfAudio.sfxOn ? "🔊 SFX" : "🔇 SFX";
  });

  setupRound();
  runCountdown();
})();
