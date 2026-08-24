/* PenFight Arena — Local Battle Controller */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const config = JSON.parse(sessionStorage.getItem("pf_local_config") || "null") || {
    player1: { name: "Player 1", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#3b82f6", accent: "#93c5fd", trail: "#60a5fa", glow: false } },
    player2: { name: "Player 2", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#f87171", accent: "#fecaca", trail: "#fca5a5", glow: false } },
  };

  document.getElementById("hud-p1-name").textContent = config.player1.name;
  document.getElementById("hud-p2-name").textContent = config.player2.name;

  canvas.style.background = `linear-gradient(135deg, ${window.PF_ARENA.fromColor}, ${window.PF_ARENA.toColor})`;

  const bench = { x: 140, y: 130, w: 620, h: 160 };
  const engine = new PenFightEngine(canvas, {
    bench,
    onSettle: handleSettle,
    onFall: handleFall,
    onCollision: (a, b, strength) => {
      pfAudio.collision(strength);
      engine.screenShake(4 + strength * 10);
    },
  });
  engine.benchColorLight = shade(window.PF_ARENA.benchColor, 24);
  engine.benchColorDark = shade(window.PF_ARENA.benchColor, -30);

  engine.addPen("p1", {
    x: bench.x + bench.w * 0.28, y: bench.y + bench.h / 2, angle: 0,
    color: config.player1.skin.color, accent: config.player1.skin.accent,
    trailColor: config.player1.skin.trail, glow: !!config.player1.skin.glow,
    mass: config.player1.pen.mass || 1, friction: config.player1.pen.friction || 1,
    assetKey: config.player1.skin.assetKey || "classic-blue"
  });
  engine.addPen("p2", {
    x: bench.x + bench.w * 0.72, y: bench.y + bench.h / 2, angle: Math.PI,
    color: config.player2.skin.color, accent: config.player2.skin.accent,
    trailColor: config.player2.skin.trail, glow: !!config.player2.skin.glow,
    mass: config.player2.pen.mass || 1, friction: config.player2.pen.friction || 1,
    assetKey: config.player2.skin.assetKey || "sunset-blaze"
  });

  const penOwner = { p1: "player1", p2: "player2" };
  const penPowerStat = { p1: config.player1.pen.power || 1, p2: config.player2.pen.power || 1 };

  let currentTurn = "p1";
  let gameOver = false;
  let waitingForSettle = false;
  let dragging = null; // {penId, anchorX, anchorY, mouseX, mouseY}

  const turnBanner = document.getElementById("turn-banner");
  const powerFill = document.getElementById("power-fill");
  const powerLabel = document.getElementById("power-label");
  const MAX_PULL = 95;

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
    if (gameOver || waitingForSettle || engine.anyPenMoving()) return;
    const pos = canvasPos(evt);
    const pen = engine.pens[currentTurn];
    if (!pen) return;
    const dist = Math.hypot(pos.x - pen.x, pos.y - pen.y);
    if (dist > 70) return; // must grab near your own pen
    dragging = { penId: currentTurn, anchorX: pen.x, anchorY: pen.y, mouseX: pos.x, mouseY: pos.y };
    pfAudio.click();
  }

  function moveDrag(evt) {
    if (!dragging) return;
    const pos = canvasPos(evt);
    dragging.mouseX = pos.x;
    dragging.mouseY = pos.y;
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
      const angle = Math.atan2(-dy, -dx); // flick away from the pull direction
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

  // draw the aim/pull line on top of the engine's own render loop
  function drawAimOverlay() {
    if (dragging) {
      const ctx = canvas.getContext("2d");
      const { anchorX, anchorY, mouseX, mouseY } = dragging;
      ctx.save();
      ctx.strokeStyle = "rgba(250, 204, 21, 0.85)";
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.moveTo(anchorX, anchorY);
      ctx.lineTo(mouseX, mouseY);
      ctx.stroke();
      // arrow showing flick direction (opposite of pull)
      const fx = anchorX - (mouseX - anchorX), fy = anchorY - (mouseY - anchorY);
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(52, 211, 153, 0.9)";
      ctx.beginPath();
      ctx.moveTo(anchorX, anchorY);
      ctx.lineTo(fx, fy);
      ctx.stroke();
      ctx.restore();
    }
    requestAnimationFrame(drawAimOverlay);
  }

  // ---------------------------------------------------------------- turns

  function handleSettle() {
    if (gameOver) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();
    }
  }

  // Fallback poll in case the last-settled pen doesn't trigger onSettle
  // (e.g. it was already stationary and only the other pen was moving).
  setInterval(() => {
    if (!gameOver && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();
    }
  }, 200);

  function handleFall(penId) {
    if (gameOver) return;
    gameOver = true;
    pfAudio.fall();
    engine.screenShake(14);
    const loserSlot = penOwner[penId];
    const winnerSlot = loserSlot === "player1" ? "player2" : "player1";
    showVictory(winnerSlot);
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
    const seq = ["3", "2", "1", "FIGHT!"];
    let i = 0;
    const step = () => {
      text.textContent = seq[i];
      if (seq[i] === "FIGHT!") { pfAudio.fight(); text.style.color = "#34d399"; }
      else { pfAudio.countdownTick(); }
      i++;
      if (i < seq.length) {
        setTimeout(step, 700);
      } else {
        setTimeout(() => {
          overlay.style.display = "none";
          engine.start();
          drawAimOverlay();
          updateTurnUI();
        }, 500);
      }
    };
    step();
  }

  function showVictory(winnerSlot) {
    const name = winnerSlot === "player1" ? config.player1.name : config.player2.name;
    document.getElementById("victory-winner").textContent = `${name.toUpperCase()} WINS`;
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
    }, 300);
  }

  document.getElementById("rematch-btn").addEventListener("click", () => window.location.reload());

  const sfxToggle = document.getElementById("sfx-toggle");
  sfxToggle.addEventListener("click", () => {
    pfAudio.setSfx(!pfAudio.sfxOn);
    sfxToggle.textContent = pfAudio.sfxOn ? "🔊 SFX" : "🔇 SFX";
  });

  runCountdown();
})();
