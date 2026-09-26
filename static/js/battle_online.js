/* PenFight Arena — Dynamic Multi-Player Online Battle Controller (2-5 Players) */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const mySlot = window.PF_MY_SLOT;

  // Multi-player room players configuration array
  const roomPlayers = window.PF_ROOM_PLAYERS || [
    { slot: "player1", username: window.PF_HOST_NAME || "Player 1", pen: window.PF_HOST_PEN || {} },
    { slot: "player2", username: window.PF_GUEST_NAME || "Player 2", pen: window.PF_GUEST_PEN || {} },
  ];

  const penConfig = {};
  const nameFor = {};
  const penIdFor = {};
  const skinIdFor = {};
  const roundWins = {};

  roomPlayers.forEach(p => {
    penConfig[p.slot] = p.pen || {};
    nameFor[p.slot] = p.username || "Player";
    penIdFor[p.slot] = (p.pen || {}).penId;
    skinIdFor[p.slot] = (p.pen || {}).skinId;
    roundWins[p.slot] = 0;
  });

  canvas.width = 960;
  canvas.height = 520;

  const engine = new PenFightEngine(canvas, {
    onSettle: handleSettle,
    onFall: handleFall,
    onCollision: (a, b, strength) => { pfAudio.collision(strength); engine.screenShake(4 + strength * 10); },
    onBumperHit: (bmp, strength) => { pfAudio.bumperHit(bmp.type, strength); engine.screenShake(2 + strength * 6); },
  });
  engine.benchColorLight = shade(window.PF_ARENA.benchColor, 24);
  engine.benchColorDark = shade(window.PF_ARENA.benchColor, -30);

  const bench = engine.bench;

  let currentRound = 1;
  let turnIndex = 0;
  let currentTurn = roomPlayers[0] ? roomPlayers[0].slot : "player1";
  let roundOver = false;
  let gameOver = false;
  let isTransitioningRound = false;
  let waitingForSettle = false;
  let dragging = null;
  let connected = false;

  // Controls
  const angleSlider = document.getElementById("angle-slider");
  const powerSlider = document.getElementById("power-slider");
  const angleValText = document.getElementById("angle-val");
  const powerValText = document.getElementById("power-val");
  const powerQualText = document.getElementById("power-qual");
  const flickBtn = document.getElementById("flick-btn");

  const roundLabel = document.getElementById("round-label");
  const scoreText = document.getElementById("score-text");
  const turnPill = document.getElementById("turn-pill");
  const connPill = document.getElementById("conn-pill");
  const MAX_PULL = 95;

  const sfxToggle = document.getElementById("sfx-toggle");
  if (sfxToggle) {
    sfxToggle.addEventListener("click", () => {
      pfAudio.setSfx(!pfAudio.sfxOn);
      sfxToggle.innerHTML = `<svg class="pf-icon"><use href="${pfAudio.sfxOn ? "#icon-volume" : "#icon-volume-off"}"></use></svg>`;
    });
  }

  function renderDynamicHUD() {
    const leftContainer = document.getElementById("hud-players-left");
    const rightContainer = document.getElementById("hud-players-right");

    if (!leftContainer || !rightContainer) return;

    leftContainer.innerHTML = "";
    rightContainer.innerHTML = "";

    const n = roomPlayers.length;
    const splitIndex = Math.ceil(n / 2);

    roomPlayers.forEach((p, idx) => {
      const card = document.createElement("div");
      card.className = `pf-ref-hud-card p${idx + 1}`;
      card.id = `hud-${p.slot}`;

      const initial = p.username.substring(0, 1).toUpperCase();
      const wins = roundWins[p.slot] || 0;
      const isCurrent = (p.slot === currentTurn);

      card.innerHTML = `
        <div class="pf-ref-player-header">
          <div class="pf-ref-avatar p${idx + 1}">${initial}</div>
          <div class="pf-ref-meta">
            <div class="pf-ref-name">${p.username}</div>
            <div class="pf-ref-rank">${p.is_host ? "HOST" : `PLAYER ${idx + 1}`}</div>
          </div>
        </div>
        <div class="pf-ref-dots">
          <div class="pf-ref-dot ${wins >= 1 ? `win-p${idx + 1}` : ""}"></div>
          <div class="pf-ref-dot ${wins >= 2 ? `win-p${idx + 1}` : ""}"></div>
        </div>
      `;

      if (isCurrent) {
        card.style.borderColor = "var(--gold)";
        card.style.boxShadow = "0 0 16px rgba(250, 204, 21, 0.3)";
      }

      if (idx < splitIndex) {
        leftContainer.appendChild(card);
      } else {
        rightContainer.appendChild(card);
      }
    });
  }

  function updateScoreHUD() {
    renderDynamicHUD();

    if (roundLabel) {
      roundLabel.textContent = `ROUND ${currentRound}`;
      roundLabel.style.color = "#94a3b8";
    }

    if (scoreText) {
      scoreText.textContent = `${roomPlayers.length} PLAYERS BATTLE`;
    }
  }

  function setupRound() {
    engine.reset();
    roundOver = false;
    isTransitioningRound = false;
    waitingForSettle = false;
    dragging = null;

    // Tabletop placement for N players (2-5)
    const N = roomPlayers.length;
    const cx = bench.x + bench.w / 2;
    const cy = bench.y + bench.h / 2;
    const rx = bench.w * 0.35;
    const ry = bench.h * 0.32;
    const angleStep = (2 * Math.PI) / N;

    roomPlayers.forEach((p, idx) => {
      const theta = idx * angleStep;
      const px = cx - rx * Math.cos(theta);
      const py = cy - ry * Math.sin(theta);
      const facingAngle = Math.atan2(cy - py, cx - px);
      const conf = penConfig[p.slot] || {};

      engine.addPen(p.slot, {
        x: px, y: py, angle: facingAngle,
        color: conf.color || "#3b82f6",
        accent: conf.accent || "#93c5fd",
        trailColor: conf.trail || "#60a5fa",
        glow: !!conf.glow,
        mass: conf.mass || 1.0,
        friction: conf.friction || 1.0,
        assetKey: conf.assetKey || "classic-blue",
      });
    });

    turnIndex = (currentRound - 1) % N;
    currentTurn = roomPlayers[turnIndex].slot;

    engine.generateBumpers(`${window.PF_ROOM_CODE}_r${currentRound}`);
    updateScoreHUD();
    updateTurnUI();
  }

  function getNextTurnSlot() {
    const N = roomPlayers.length;
    for (let i = 1; i <= N; i++) {
      const candidateIdx = (turnIndex + i) % N;
      const candidateSlot = roomPlayers[candidateIdx].slot;
      const pen = engine.pens[candidateSlot];
      if (pen && pen.alive && !pen.falling) {
        turnIndex = candidateIdx;
        return candidateSlot;
      }
    }
    return roomPlayers[turnIndex].slot;
  }

  function updateTurnUI() {
    const curPlayerName = nameFor[currentTurn] || "PLAYER";
    if (turnPill) {
      turnPill.textContent = `${curPlayerName.toUpperCase()}'S TURN`;
      turnPill.style.borderColor = (currentTurn === mySlot) ? "rgba(52, 211, 153, 0.8)" : "rgba(99, 102, 241, 0.5)";
    }

    const pen = engine.pens[currentTurn];
    const defaultAngle = pen ? Math.round((pen.angle * 180) / Math.PI) % 360 : 0;
    const normalizedAngle = defaultAngle < 0 ? defaultAngle + 360 : defaultAngle;

    if (angleSlider) {
      angleSlider.value = normalizedAngle;
      if (angleValText) angleValText.textContent = `${normalizedAngle}°`;
    }
  }

  // ---------------------------------------------------------------- WebSockets
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${scheme}://${window.location.host}/ws/battle/${window.PF_ROOM_CODE}/`);

  socket.addEventListener("open", () => {
    connected = true;
    if (connPill) {
      connPill.textContent = "Connected";
      connPill.classList.remove("bad"); connPill.classList.add("ok");
    }
    setupRound();
    runCountdown();
  });

  socket.addEventListener("close", () => {
    if (connPill) {
      connPill.textContent = "Disconnected";
      connPill.classList.remove("ok"); connPill.classList.add("bad");
    }
  });

  socket.addEventListener("message", (evt) => {
    const data = JSON.parse(evt.data);
    if (data.kind === "flick" && data.slot !== mySlot) {
      engine.flick(data.slot, data.angle, data.power);
      pfAudio.flick();
      waitingForSettle = true;
    } else if (data.kind === "opponent_left") {
      if (data.slot && data.slot !== mySlot && !gameOver) {
        const discOverlay = document.getElementById("disconnect-overlay");
        if (discOverlay) discOverlay.style.display = "flex";
      }
    } else if (data.kind === "match_over") {
      handleMatchOver(data);
    }
  });

  function send(payload) {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(payload));
  }

  // ---------------------------------------------------------------- Dual Aiming Controls
  if (angleSlider) {
    angleSlider.addEventListener("input", () => {
      if (angleValText) angleValText.textContent = `${angleSlider.value}°`;
    });
  }

  if (powerSlider) {
    powerSlider.addEventListener("input", () => {
      const p = parseInt(powerSlider.value, 10);
      if (powerValText) powerValText.textContent = `${p}%`;
      if (powerQualText) {
        if (p < 34) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
        else if (p < 70) { powerQualText.textContent = "MEDIUM"; powerQualText.style.color = "#facc15"; }
        else { powerQualText.textContent = "HIGH"; powerQualText.style.color = "#f87171"; }
      }
    });
  }

  if (flickBtn) {
    flickBtn.addEventListener("click", () => {
      if (gameOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving() || currentTurn !== mySlot) return;
      const powerNorm = parseInt(powerSlider.value, 10) / 100;
      if (powerNorm <= 0.04) return;
      const angleRad = (parseInt(angleSlider.value, 10) * Math.PI) / 180;

      const conf = penConfig[mySlot] || {};
      const scaledPower = powerNorm * (conf.power || 1);
      engine.flick(mySlot, angleRad, scaledPower);
      pfAudio.flick();
      waitingForSettle = true;
      send({ kind: "flick", angle: angleRad, power: scaledPower });

      powerSlider.value = 0;
      if (powerValText) powerValText.textContent = "0%";
      if (powerQualText) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
    });
  }

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
    const powerNorm = pull / MAX_PULL;
    const angleRad = Math.atan2(-dy, -dx);
    let deg = Math.round((angleRad * 180) / Math.PI);
    if (deg < 0) deg += 360;

    if (angleSlider) angleSlider.value = deg;
    if (angleValText) angleValText.textContent = `${deg}°`;
    const powPct = Math.round(powerNorm * 100);
    if (powerSlider) powerSlider.value = powPct;
    if (powerValText) powerValText.textContent = `${powPct}%`;
    if (powerQualText) {
      if (powPct < 34) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
      else if (powPct < 70) { powerQualText.textContent = "MEDIUM"; powerQualText.style.color = "#facc15"; }
      else { powerQualText.textContent = "HIGH"; powerQualText.style.color = "#f87171"; }
    }
  }

  function endDrag() {
    if (!dragging) return;
    const dx = dragging.mouseX - dragging.anchorX, dy = dragging.mouseY - dragging.anchorY;
    const pull = Math.min(MAX_PULL, Math.hypot(dx, dy));
    const power = pull / MAX_PULL;
    if (power > 0.08) {
      const angle = Math.atan2(-dy, -dx);
      const conf = penConfig[mySlot] || {};
      const scaledPower = power * (conf.power || 1);
      engine.flick(mySlot, angle, scaledPower);
      pfAudio.flick();
      waitingForSettle = true;
      send({ kind: "flick", angle, power: scaledPower });
    }
    dragging = null;
    if (powerSlider) powerSlider.value = 0;
    if (powerValText) powerValText.textContent = "0%";
    if (powerQualText) { powerQualText.textContent = "LOW"; powerQualText.style.color = "#34d399"; }
  }

  canvas.addEventListener("mousedown", startDrag);
  canvas.addEventListener("mousemove", moveDrag);
  window.addEventListener("mouseup", endDrag);
  canvas.addEventListener("touchstart", (e) => { startDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchmove", (e) => { moveDrag(e); e.preventDefault(); }, { passive: false });
  canvas.addEventListener("touchend", endDrag);

  function drawAimOverlay() {
    const ctx = canvas.getContext("2d");
    const pen = engine.pens[mySlot];

    if (pen && pen.alive && !engine.anyPenMoving() && !waitingForSettle && !roundOver && !gameOver && currentTurn === mySlot) {
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

  // ---------------------------------------------------------------- Turns & Settling
  function handleSettle() {
    if (gameOver || roundOver || isTransitioningRound) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = getNextTurnSlot();
      updateTurnUI();
      updateScoreHUD();
    }
  }

  setInterval(() => {
    if (!gameOver && !roundOver && !isTransitioningRound && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = getNextTurnSlot();
      updateTurnUI();
      updateScoreHUD();
    }
  }, 200);

  function handleFall(penId) {
    if (roundOver || gameOver || isTransitioningRound) return;

    pfAudio.fall();
    engine.screenShake(14);

    const survivingPens = roomPlayers.filter(p => {
      const pen = engine.pens[p.slot];
      return pen && pen.alive && !pen.falling && p.slot !== penId;
    });

    if (survivingPens.length <= 1) {
      roundOver = true;
      isTransitioningRound = true;

      const roundWinnerSlot = survivingPens[0] ? survivingPens[0].slot : roomPlayers[0].slot;
      roundWins[roundWinnerSlot] = (roundWins[roundWinnerSlot] || 0) + 1;
      updateScoreHUD();

      if (roundWins[roundWinnerSlot] >= 2) {
        gameOver = true;
        const penIdsMap = {};
        roomPlayers.forEach(p => {
          penIdsMap[`${p.slot}_pen`] = penIdFor[p.slot];
          penIdsMap[`${p.slot}_skin`] = skinIdFor[p.slot];
        });

        send({
          kind: "pen_out",
          slot: penId,
          winner_slot: roundWinnerSlot,
          pen_ids: penIdsMap,
        });
      } else {
        const winnerName = nameFor[roundWinnerSlot] || "PLAYER";
        showRoundToast(winnerName, currentRound, () => {
          currentRound++;
          isTransitioningRound = false;
          setupRound();
          runCountdown();
        });
      }
    }
  }

  function showRoundToast(winnerName, roundNum, onComplete) {
    const toast = document.createElement("div");
    toast.className = "pf-overlay";
    toast.innerHTML = `
      <div class="pf-center">
        <div class="pf-faint" style="letter-spacing:0.18em; font-size:14px; text-transform:uppercase;">ROUND ${roundNum} RESULT</div>
        <div style="font-family:var(--font-display); font-size:52px; font-weight:900; color:var(--gold); margin-top:8px;">${winnerName.toUpperCase()} WINS ROUND ${roundNum}</div>
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
    const winMsg = `${(data.winner_username || "PLAYER").toUpperCase()} WINS THE MATCH!`;
    const victoryWinnerEl = document.getElementById("victory-winner");
    if (victoryWinnerEl) victoryWinnerEl.textContent = winMsg;

    if (iWon) pfAudio.victory(); else pfAudio.defeat();

    const myRewards = iWon ? data.winner_rewards : data.loser_rewards;
    const box = document.getElementById("victory-rewards");
    if (box && myRewards) {
      box.innerHTML = `
        <div class="pf-badge pf-badge-legendary" style="display:inline-flex; align-items:center; gap:6px;"><span class="pf-icon" style="color:var(--gold);"><svg><use href="#icon-coin"></use></svg></span> +${myRewards.pp || 0} PP</div>
        <div class="pf-badge pf-badge-rare" style="display:inline-flex; align-items:center; gap:6px;"><span class="pf-icon"><svg><use href="#icon-star"></use></svg></span> +${myRewards.xp || 0} XP</div>
        ${myRewards.streak_bonus ? `<div class="pf-badge pf-badge-epic" style="display:inline-flex; align-items:center; gap:6px;"><span class="pf-icon"><svg><use href="#icon-flame"></use></svg></span> +${myRewards.streak_bonus} Streak Bonus</div>` : ""}
      `;
      if (iWon) {
        (data.winner_achievements || []).forEach((a) => {
          const div = document.createElement("div");
          div.className = "pf-badge pf-badge-mythic";
          div.textContent = `${a.name}`;
          box.appendChild(div);
        });
      }
    }
    const victoryOverlay = document.getElementById("victory-overlay");
    if (victoryOverlay) setTimeout(() => { victoryOverlay.style.display = "flex"; }, 400);
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
    if (!overlay || !text) {
      if (!engine.running) {
        engine.start();
        drawAimOverlay();
      }
      updateTurnUI();
      return;
    }
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
