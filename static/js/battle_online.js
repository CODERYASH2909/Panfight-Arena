/* PenFight Arena — Online Battle Controller (Best-of-3 System) */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const mySlot = window.PF_MY_SLOT;
  const opponentSlot = mySlot === "player1" ? "player2" : "player1";

  const penConfig = {
    player1: window.PF_HOST_PEN,
    player2: window.PF_GUEST_PEN,
  };
  const nameFor = { player1: window.PF_HOST_NAME, player2: window.PF_GUEST_NAME };
  const penIdFor = { player1: window.PF_HOST_PEN.penId, player2: window.PF_GUEST_PEN.penId };
  const skinIdFor = { player1: window.PF_HOST_PEN.skinId, player2: window.PF_GUEST_PEN.skinId };

  canvas.width = 960;
  canvas.height = 520;
  canvas.style.background = `linear-gradient(135deg, ${window.PF_ARENA.fromColor}, ${window.PF_ARENA.toColor})`;

  const engine = new PenFightEngine(canvas, {
    onSettle: handleSettle,
    onFall: handleFall,
    onCollision: (a, b, strength) => { pfAudio.collision(strength); engine.screenShake(4 + strength * 10); },
    onBumperHit: (bmp, strength) => { pfAudio.bumperHit(bmp.type, strength); engine.screenShake(2 + strength * 6); },
  });
  engine.benchColorLight = shade(window.PF_ARENA.benchColor, 24);
  engine.benchColorDark = shade(window.PF_ARENA.benchColor, -30);

  // Authoritative tabletop bounds (occupying ~94% of canvas area)
  const bench = engine.bench;

  // Best-of-3 Online Match State Machine
  let currentRound = 1;
  let p1RoundWins = 0;
  let p2RoundWins = 0;

  let currentTurn = "player1";
  let roundOver = false;
  let gameOver = false;
  let isTransitioningRound = false;
  let waitingForSettle = false;
  let dragging = null;
  let connected = false;

  const turnBanner = document.getElementById("turn-banner");
  const roundBanner = document.getElementById("round-banner");
  const powerFill = document.getElementById("power-fill");
  const powerLabel = document.getElementById("power-label");
  const hintText = document.getElementById("hint-text");
  const connPill = document.getElementById("conn-pill");
  const p1WinsDot = document.getElementById("p1-wins-dots");
  const p2WinsDot = document.getElementById("p2-wins-dots");
  const MAX_PULL = 95;

  const sfxToggle = document.getElementById("sfx-toggle");
  sfxToggle.addEventListener("click", () => {
    pfAudio.setSfx(!pfAudio.sfxOn);
    sfxToggle.textContent = pfAudio.sfxOn ? "🔊 SFX" : "🔇 SFX";
  });

  function updateScoreHUD() {
    if (p1WinsDot) p1WinsDot.textContent = "●".repeat(p1RoundWins) + "○".repeat(2 - p1RoundWins);
    if (p2WinsDot) p2WinsDot.textContent = "●".repeat(p2RoundWins) + "○".repeat(2 - p2RoundWins);
    if (roundBanner) {
      if (p1RoundWins === 1 && p2RoundWins === 1) {
        roundBanner.textContent = "FINAL ROUND (1 — 1)";
        roundBanner.style.color = "var(--gold)";
      } else {
        roundBanner.textContent = `ROUND ${currentRound}`;
        roundBanner.style.color = "var(--text-secondary)";
      }
    }
  }

  function setupRound() {
    engine.reset();
    roundOver = false;
    isTransitioningRound = false;
    waitingForSettle = false;
    dragging = null;
    currentTurn = (currentRound % 2 === 1) ? "player1" : "player2";

    engine.addPen("player1", {
      x: bench.x + bench.w * 0.15, y: bench.y + bench.h / 2, angle: 0,
      color: penConfig.player1.color, accent: penConfig.player1.accent,
      trailColor: penConfig.player1.trail, glow: !!penConfig.player1.glow,
      mass: penConfig.player1.mass || 1, friction: penConfig.player1.friction || 1,
      assetKey: penConfig.player1.assetKey || "classic-blue"
    });
    engine.addPen("player2", {
      x: bench.x + bench.w * 0.85, y: bench.y + bench.h / 2, angle: Math.PI,
      color: penConfig.player2.color, accent: penConfig.player2.accent,
      trailColor: penConfig.player2.trail, glow: !!penConfig.player2.glow,
      mass: penConfig.player2.mass || 1, friction: penConfig.player2.friction || 1,
      assetKey: penConfig.player2.assetKey || "sunset-blaze"
    });

    // Seed-based procedural bumpers (deterministic for room code + round)
    engine.generateBumpers(`${window.PF_ROOM_CODE}_r${currentRound}`);
    updateScoreHUD();
    updateTurnUI();
  }

  function updateTurnUI() {
    document.getElementById("hud-p1").classList.toggle("active-turn", currentTurn === "player1");
    document.getElementById("hud-p2").classList.toggle("active-turn", currentTurn === "player2");
    turnBanner.textContent = `${nameFor[currentTurn].toUpperCase()}'S TURN`;
    hintText.textContent = currentTurn === mySlot
      ? "Your turn — drag your pen backward, then release to flick."
      : `Waiting for ${nameFor[currentTurn]} to flick...`;
  }

  // ---------------------------------------------------------------- ws

  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${scheme}://${window.location.host}/ws/battle/${window.PF_ROOM_CODE}/`);

  socket.addEventListener("open", () => {
    connected = true;
    connPill.textContent = "Connected";
    connPill.classList.remove("bad"); connPill.classList.add("ok");
    setupRound();
    runCountdown();
  });
  socket.addEventListener("close", () => {
    connPill.textContent = "Disconnected";
    connPill.classList.remove("ok"); connPill.classList.add("bad");
  });

  socket.addEventListener("message", (evt) => {
    const data = JSON.parse(evt.data);
    if (data.kind === "flick" && data.slot !== mySlot) {
      engine.flick(data.slot, data.angle, data.power);
      pfAudio.flick();
      waitingForSettle = true;
    } else if (data.kind === "opponent_left") {
      if (data.slot && data.slot !== mySlot && !gameOver) {
        document.getElementById("disconnect-overlay").style.display = "flex";
      }
    } else if (data.kind === "match_over") {
      handleMatchOver(data);
    }
  });

  function send(payload) {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload));
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
    if (gameOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving() || currentTurn !== mySlot) return;
    const pos = canvasPos(evt);
    const pen = engine.pens[mySlot];
    if (!pen) return;
    const dist = Math.hypot(pos.x - pen.x, pos.y - pen.y);
    if (dist > 75) return;
    dragging = { anchorX: pen.x, anchorY: pen.y, mouseX: pos.x, mouseY: pos.y };
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
      const scaledPower = power * (penConfig[mySlot].power || 1);
      engine.flick(mySlot, angle, scaledPower);
      pfAudio.flick();
      waitingForSettle = true;
      send({ kind: "flick", angle, power: scaledPower });
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

  // ---------------------------------------------------------------- turns

  function handleSettle() {
    if (gameOver || roundOver || isTransitioningRound) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = currentTurn === "player1" ? "player2" : "player1";
      updateTurnUI();
    }
  }
  setInterval(() => {
    if (!gameOver && !roundOver && !isTransitioningRound && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = currentTurn === "player1" ? "player2" : "player1";
      updateTurnUI();
    }
  }, 200);

  function handleFall(penId) {
    if (roundOver || gameOver || isTransitioningRound) return;
    roundOver = true;
    isTransitioningRound = true;
    pfAudio.fall();
    engine.screenShake(14);

    const loserSlot = penId;
    const winnerSlot = loserSlot === "player1" ? "player2" : "player1";
    if (winnerSlot === "player1") p1RoundWins++; else p2RoundWins++;
    updateScoreHUD();

    if (p1RoundWins >= 2 || p2RoundWins >= 2) {
      gameOver = true;
      send({
        kind: "pen_out", slot: penId,
        pen_ids: {
          player1_pen: penIdFor.player1, player1_skin: skinIdFor.player1,
          player2_pen: penIdFor.player2, player2_skin: skinIdFor.player2,
        },
      });
    } else {
      showRoundToast(nameFor[winnerSlot], currentRound, p1RoundWins, p2RoundWins, () => {
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

  function handleMatchOver(data) {
    gameOver = true;
    const iWon = data.winner_slot === mySlot;
    document.getElementById("victory-winner").textContent = `${data.winner_username.toUpperCase()} WINS THE MATCH (${p1RoundWins} - ${p2RoundWins})`;
    if (iWon) pfAudio.victory(); else pfAudio.defeat();

    const myRewards = iWon ? data.winner_rewards : data.loser_rewards;
    const box = document.getElementById("victory-rewards");
    box.innerHTML = `
      <div class="pf-badge pf-badge-legendary">🪙 +${myRewards.pp || 0} PP</div>
      <div class="pf-badge pf-badge-rare">⭐ +${myRewards.xp || 0} XP</div>
      ${myRewards.streak_bonus ? `<div class="pf-badge pf-badge-epic">🔥 +${myRewards.streak_bonus} Streak Bonus</div>` : ""}
    `;
    if (iWon) {
      (data.winner_achievements || []).forEach((a) => {
        const div = document.createElement("div");
        div.className = "pf-badge pf-badge-mythic";
        div.textContent = `${a.icon} ${a.name}`;
        box.appendChild(div);
      });
    }
    setTimeout(() => { document.getElementById("victory-overlay").style.display = "flex"; }, 400);
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
})();
