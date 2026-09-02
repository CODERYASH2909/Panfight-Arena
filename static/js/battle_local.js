/* PenFight Arena — Local Battle Controller (Reference Image UI & Dual Aiming) */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const config = JSON.parse(sessionStorage.getItem("pf_local_config") || "null") || {
    player1: { name: "YASH", rank: "ROOKIE", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#3b82f6", accent: "#93c5fd", trail: "#60a5fa", glow: false } },
    player2: { name: "PLAYER 2", rank: "APPRENTICE", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#f87171", accent: "#fecaca", trail: "#fca5a5", glow: false } },
  };

  const p1Name = config.player1.name || "YASH";
  const p2Name = config.player2.name || "PLAYER 2";

  document.getElementById("hud-p1-name").textContent = p1Name.toUpperCase();
  document.getElementById("hud-p1-avatar").textContent = p1Name.charAt(0).toUpperCase();
  document.getElementById("hud-p1-rank").textContent = `RANK: ${config.player1.rank || "ROOKIE"}`;

  document.getElementById("hud-p2-name").textContent = p2Name.toUpperCase();
  document.getElementById("hud-p2-avatar").textContent = p2Name.charAt(0).toUpperCase();
  document.getElementById("hud-p2-rank").textContent = `RANK: ${config.player2.rank || "APPRENTICE"}`;

  canvas.width = 960;
  canvas.height = 520;

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

  // Slider Dual Control Elements
  const angleSlider = document.getElementById("angle-slider");
  const powerSlider = document.getElementById("power-slider");
  const angleValText = document.getElementById("angle-val");
  const powerValText = document.getElementById("power-val");
  const powerQualText = document.getElementById("power-qual");
  const flickBtn = document.getElementById("flick-btn");

  const roundLabel = document.getElementById("round-label");
  const scoreText = document.getElementById("score-text");
  const turnPill = document.getElementById("turn-pill");
  const MAX_PULL = 95;

  function updateScoreHUD() {
    scoreText.textContent = `${p1RoundWins} — ${p2RoundWins}`;

    // Update Win Dots
    const dot1P1 = document.getElementById("p1-dot-1");
    const dot2P1 = document.getElementById("p1-dot-2");
    if (dot1P1) dot1P1.className = `pf-ref-dot ${p1RoundWins >= 1 ? "win-p1" : ""}`;
    if (dot2P1) dot2P1.className = `pf-ref-dot ${p1RoundWins >= 2 ? "win-p1" : ""}`;

    const dot1P2 = document.getElementById("p2-dot-1");
    const dot2P2 = document.getElementById("p2-dot-2");
    if (dot1P2) dot1P2.className = `pf-ref-dot ${p2RoundWins >= 1 ? "win-p2" : ""}`;
    if (dot2P2) dot2P2.className = `pf-ref-dot ${p2RoundWins >= 2 ? "win-p2" : ""}`;

    if (p1RoundWins === 1 && p2RoundWins === 1) {
      roundLabel.textContent = "FINAL ROUND";
      roundLabel.style.color = "var(--gold)";
    } else {
      roundLabel.textContent = `ROUND ${currentRound}`;
      roundLabel.style.color = "#94a3b8";
    }
  }

  function setupRound() {
    engine.reset();
    roundOver = false;
    isTransitioningRound = false;
    waitingForSettle = false;
    dragging = null;
    currentTurn = (currentRound % 2 === 1) ? "p1" : "p2";

    // Pens start 15% and 85% from left edge of tabletop (~638px distance apart)
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

    engine.generateBumpers(`local_r${currentRound}_${Date.now()}`);
    updateScoreHUD();
    updateTurnUI();
  }

  function updateTurnUI() {
    const name = currentTurn === "p1" ? p1Name : p2Name;
    turnPill.textContent = `${name.toUpperCase()}'S TURN`;
    turnPill.style.borderColor = currentTurn === "p1" ? "rgba(59, 130, 246, 0.5)" : "rgba(239, 68, 68, 0.5)";

    // Default angle slider pointing toward opponent
    const defaultAngle = currentTurn === "p1" ? 0 : 180;
    angleSlider.value = defaultAngle;
    angleValText.textContent = `${defaultAngle}°`;
  }

  // ---------------------------------------------------------------- dual aiming

  angleSlider.addEventListener("input", () => {
    angleValText.textContent = `${angleSlider.value}°`;
  });

  powerSlider.addEventListener("input", () => {
    const p = parseInt(powerSlider.value, 10);
    powerValText.textContent = `${p}%`;
    if (p < 34) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
    else if (p < 70) { powerQualText.textContent = "MEDIUM"; powerQualText.style.color = "#facc15"; }
    else { powerQualText.textContent = "HIGH"; powerQualText.style.color = "#f87171"; }
  });

  flickBtn.addEventListener("click", () => {
    if (matchOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving()) return;
    const powerNorm = parseInt(powerSlider.value, 10) / 100;
    if (powerNorm <= 0.04) return;
    const angleRad = (parseInt(angleSlider.value, 10) * Math.PI) / 180;

    engine.flick(currentTurn, angleRad, powerNorm * (penPowerStat[currentTurn] || 1));
    pfAudio.flick();
    waitingForSettle = true;

    // Reset slider UI
    powerSlider.value = 0;
    powerValText.textContent = "0%";
    powerQualText.textContent = "LOW";
  });

  // Canvas Drag Aiming
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
    const powerNorm = pull / MAX_PULL;
    const angleRad = Math.atan2(-dy, -dx);
    let deg = Math.round((angleRad * 180) / Math.PI);
    if (deg < 0) deg += 360;

    // Sync sliders
    angleSlider.value = deg;
    angleValText.textContent = `${deg}°`;
    const powPct = Math.round(powerNorm * 100);
    powerSlider.value = powPct;
    powerValText.textContent = `${powPct}%`;
    if (powPct < 34) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
    else if (powPct < 70) { powerQualText.textContent = "MEDIUM"; powerQualText.style.color = "#facc15"; }
    else { powerQualText.textContent = "HIGH"; powerQualText.style.color = "#f87171"; }
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
    powerSlider.value = 0;
    powerValText.textContent = "0%";
    powerQualText.textContent = "LOW";
  }

  canvas.addEventListener("mousedown", startDrag);
  canvas.addEventListener("mousemove", moveDrag);
  window.addEventListener("mouseup", endDrag);
  canvas.addEventListener("touchstart", (e) => { startDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchmove", (e) => { moveDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchend", endDrag);

  function drawAimOverlay() {
    const ctx = canvas.getContext("2d");
    const pen = engine.pens[currentTurn];

    if (pen && pen.alive && !engine.anyPenMoving() && !waitingForSettle && !roundOver && !matchOver) {
      const angleRad = (parseInt(angleSlider.value, 10) * Math.PI) / 180;
      const powerNorm = parseInt(powerSlider.value, 10) / 100;
      const rayLen = 40 + powerNorm * 120;

      ctx.save();
      ctx.strokeStyle = "rgba(52, 211, 153, 0.85)";
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.moveTo(pen.x, pen.y);
      ctx.lineTo(pen.x + Math.cos(angleRad) * rayLen, pen.y + Math.sin(angleRad) * rayLen);
      ctx.stroke();
      ctx.restore();
    }

    if (dragging) {
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

    const winnerName = winnerSlot === "player1" ? p1Name : p2Name;

    if (p1RoundWins >= 2 || p2RoundWins >= 2) {
      matchOver = true;
      showVictory(winnerSlot);
    } else {
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
        ${isFinalNext ? `<div class="pf-badge pf-badge-mythic" style="margin-top:16px; font-size:14px; padding:6px 16px; display:inline-flex; align-items:center; gap:6px;"><span class="pf-icon"><svg><use href="#icon-flame"></use></svg></span> FINAL ROUND NEXT!</div>` : ""}
        <div class="pf-muted pf-mt-24" style="font-size:13px;">Preparing next round...</div>
      </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      document.body.removeChild(toast);
      onComplete();
    }, 2500);
  }

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
      if (seq[i] === "FIGHT!") { pfAudio.fight(); text.style.color = "#34d399"; } else { pfAudio.countdownTick(); }
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
    const name = winnerSlot === "player1" ? p1Name : p2Name;
    document.getElementById("victory-winner").textContent = `${name.toUpperCase()} WINS MATCH (${p1RoundWins} - ${p2RoundWins})`;
    if (winnerSlot === "player1") pfAudio.victory(); else pfAudio.defeat();

    fetch(window.PF_LOCAL_RESULT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": window.PF_CSRF },
      body: JSON.stringify({ winner: winnerSlot }),
    }).catch(() => {});

    setTimeout(() => {
      document.getElementById("victory-overlay").style.display = "flex";
    }, 400);
  }

  document.getElementById("rematch-btn").addEventListener("click", () => window.location.reload());

  const sfxToggle = document.getElementById("sfx-toggle");
  const sfxIcon = document.getElementById("sfx-icon");
  sfxToggle.addEventListener("click", () => {
    pfAudio.setSfx(!pfAudio.sfxOn);
    if (sfxIcon) {
      sfxIcon.innerHTML = pfAudio.sfxOn ? '<svg><use href="#icon-volume"></use></svg>' : '<svg><use href="#icon-volume-off"></use></svg>';
    }
  });

  setupRound();
  runCountdown();
})();
