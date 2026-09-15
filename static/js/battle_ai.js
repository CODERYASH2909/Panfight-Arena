/* =========================================================================
   PENFIGHT ARENA — AI Battle Controller
   A real gameplay AI that works ON TOP of the existing physics engine.
   The AI analyzes game state and decides angle + power, then uses
   engine.flick() — no physics modifications whatsoever.
   ========================================================================= */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const config = JSON.parse(sessionStorage.getItem("pf_ai_config") || "null") || {
    player1: { name: "PLAYER", rank: "ROOKIE", pen: { mass: 1, friction: 1, power: 1 }, skin: { color: "#3b82f6", accent: "#93c5fd", trail: "#60a5fa", glow: false } },
    difficulty: "normal",
  };

  const difficulty = (config.difficulty || "normal").toLowerCase();
  const p1Name = config.player1.name || "PLAYER";

  // AI identity
  const AI_NAMES = { easy: "CADET", normal: "SENTINEL", hard: "OVERLORD" };
  const AI_RANKS = { easy: "APPRENTICE", normal: "VETERAN", hard: "GRANDMASTER" };
  const aiName = `AI ${AI_NAMES[difficulty] || "SENTINEL"}`;
  const aiRank = AI_RANKS[difficulty] || "VETERAN";

  document.getElementById("hud-p1-name").textContent = p1Name.toUpperCase();
  document.getElementById("hud-p1-avatar").textContent = p1Name.charAt(0).toUpperCase();
  document.getElementById("hud-p1-rank").textContent = `RANK: ${config.player1.rank || "ROOKIE"}`;

  document.getElementById("hud-p2-name").textContent = aiName;
  document.getElementById("hud-p2-avatar").textContent = "AI";
  document.getElementById("hud-p2-rank").textContent = `RANK: ${aiRank}`;

  // Add AI indicator style to p2 card
  const p2Card = document.getElementById("hud-p2");
  if (p2Card) {
    p2Card.style.borderColor = "rgba(239, 68, 68, 0.35)";
  }

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
  const penPowerStat = { p1: config.player1.pen.power || 1, p2: 1 };

  // Best-of-3 Match State Machine
  let currentRound = 1;
  let p1RoundWins = 0;
  let p2RoundWins = 0;

  let currentTurn = "p1";
  let roundOver = false;
  let matchOver = false;
  let isTransitioningRound = false;
  let waitingForSettle = false;
  let aiThinking = false;
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

  // AI thinking overlay element
  const aiThinkingEl = document.getElementById("ai-thinking-overlay");

  function updateScoreHUD() {
    scoreText.textContent = `${p1RoundWins} — ${p2RoundWins}`;

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
    aiThinking = false;
    dragging = null;
    currentTurn = (currentRound % 2 === 1) ? "p1" : "p2";

    engine.addPen("p1", {
      x: bench.x + bench.w * 0.15, y: bench.y + bench.h / 2, angle: 0,
      color: config.player1.skin.color, accent: config.player1.skin.accent,
      trailColor: config.player1.skin.trail, glow: !!config.player1.skin.glow,
      mass: config.player1.pen.mass || 1, friction: config.player1.pen.friction || 1,
      assetKey: config.player1.skin.assetKey || "classic-blue"
    });
    engine.addPen("p2", {
      x: bench.x + bench.w * 0.85, y: bench.y + bench.h / 2, angle: Math.PI,
      color: "#dc2626", accent: "#fca5a5",
      trailColor: "#f87171", glow: false,
      mass: 1, friction: 1,
      assetKey: "inferno"
    });

    engine.generateBumpers(`ai_r${currentRound}_${Date.now()}`);
    updateScoreHUD();
    updateTurnUI();
  }

  function updateTurnUI() {
    if (currentTurn === "p1") {
      turnPill.textContent = `${p1Name.toUpperCase()}'S TURN`;
      turnPill.style.borderColor = "rgba(59, 130, 246, 0.5)";
      showControls(true);
    } else {
      turnPill.textContent = `${aiName}'S TURN`;
      turnPill.style.borderColor = "rgba(239, 68, 68, 0.5)";
      showControls(false);
    }
    const defaultAngle = currentTurn === "p1" ? 0 : 180;
    angleSlider.value = defaultAngle;
    angleValText.textContent = `${defaultAngle}°`;
  }

  function showControls(visible) {
    const bar = document.querySelector(".pf-ref-bottom-bar");
    if (bar) bar.style.opacity = visible ? "1" : "0.35";
  }

  // ================================================================
  // AI BRAIN — Analyzes game state and picks angle + power
  // ================================================================

  const AI_CONFIG = {
    easy: {
      thinkingTimeMin: 800, thinkingTimeMax: 1500,
      angleError: 25,      // degrees of random error
      powerMin: 0.25, powerMax: 0.65,
      powerError: 0.15,
      directShotChance: 0.85,
      bankShotChance: 0.05,
      edgePushChance: 0.10,
    },
    normal: {
      thinkingTimeMin: 600, thinkingTimeMax: 1200,
      angleError: 12,
      powerMin: 0.30, powerMax: 0.75,
      powerError: 0.08,
      directShotChance: 0.60,
      bankShotChance: 0.20,
      edgePushChance: 0.20,
    },
    hard: {
      thinkingTimeMin: 500, thinkingTimeMax: 1000,
      angleError: 5,
      powerMin: 0.35, powerMax: 0.85,
      powerError: 0.04,
      directShotChance: 0.40,
      bankShotChance: 0.30,
      edgePushChance: 0.30,
    },
  };

  function aiAnalyzeAndShoot() {
    const cfg = AI_CONFIG[difficulty] || AI_CONFIG.normal;
    const aiPen = engine.pens["p2"];
    const playerPen = engine.pens["p1"];
    if (!aiPen || !playerPen || !aiPen.alive || !playerPen.alive) return;

    // Calculate key metrics
    const dx = playerPen.x - aiPen.x;
    const dy = playerPen.y - aiPen.y;
    const distToPlayer = Math.hypot(dx, dy);
    const directAngle = Math.atan2(dy, dx);

    // Table edge distances for player pen (used for edge push strategy)
    const playerEdgeDistances = {
      left: playerPen.x - bench.x,
      right: (bench.x + bench.w) - playerPen.x,
      top: playerPen.y - bench.y,
      bottom: (bench.y + bench.h) - playerPen.y,
    };
    const playerNearestEdge = Math.min(...Object.values(playerEdgeDistances));
    const playerNearestEdgeName = Object.keys(playerEdgeDistances).find(
      k => playerEdgeDistances[k] === playerNearestEdge
    );

    // AI's own edge distances (for self-preservation)
    const aiEdgeDistances = {
      left: aiPen.x - bench.x,
      right: (bench.x + bench.w) - aiPen.x,
      top: aiPen.y - bench.y,
      bottom: (bench.y + bench.h) - aiPen.y,
    };
    const aiNearestEdge = Math.min(...Object.values(aiEdgeDistances));

    // Decision: choose strategy
    let chosenAngle, chosenPower;
    const roll = Math.random();

    if (playerNearestEdge < 80 && roll < cfg.edgePushChance + 0.3) {
      // EDGE PUSH STRATEGY: Player is near an edge, push them off
      const result = computeEdgePushShot(aiPen, playerPen, playerNearestEdgeName, cfg);
      chosenAngle = result.angle;
      chosenPower = result.power;
    } else if (roll < cfg.directShotChance) {
      // DIRECT SHOT: Aim at opponent
      chosenAngle = directAngle;
      chosenPower = computeDirectShotPower(distToPlayer, cfg);
    } else if (roll < cfg.directShotChance + cfg.bankShotChance) {
      // BANK SHOT: Try to bounce off a bumper toward the opponent
      const bankResult = computeBankShot(aiPen, playerPen, cfg);
      chosenAngle = bankResult.angle;
      chosenPower = bankResult.power;
    } else {
      // STRATEGIC POSITIONING: Move to a better position
      chosenAngle = computePositioningAngle(aiPen, playerPen, cfg);
      chosenPower = cfg.powerMin + Math.random() * 0.15;
    }

    // Self-preservation: if AI is near edge, bias away from it
    if (aiNearestEdge < 60) {
      const centerAngle = Math.atan2(
        (bench.y + bench.h / 2) - aiPen.y,
        (bench.x + bench.w / 2) - aiPen.x
      );
      // Blend toward center more aggressively as edge gets closer
      const edgePanic = 1 - (aiNearestEdge / 60);
      chosenAngle = lerpAngle(chosenAngle, centerAngle, edgePanic * 0.5);
      chosenPower = Math.max(chosenPower * 0.6, cfg.powerMin);
    }

    // Apply difficulty-based error
    const angleError = ((Math.random() - 0.5) * 2 * cfg.angleError * Math.PI) / 180;
    chosenAngle += angleError;

    const powerError = (Math.random() - 0.5) * 2 * cfg.powerError;
    chosenPower = Math.max(cfg.powerMin, Math.min(cfg.powerMax, chosenPower + powerError));

    return { angle: chosenAngle, power: chosenPower };
  }

  function computeDirectShotPower(dist, cfg) {
    // Scale power based on distance
    const normalizedDist = Math.min(1, dist / (bench.w * 0.7));
    let power = cfg.powerMin + normalizedDist * (cfg.powerMax - cfg.powerMin);
    // Add a bit more power for farther shots
    if (dist > bench.w * 0.5) power = Math.min(cfg.powerMax, power * 1.1);
    return power;
  }

  function computeEdgePushShot(aiPen, playerPen, edgeName, cfg) {
    // Push player toward their nearest edge
    let targetX, targetY;
    switch (edgeName) {
      case "left":   targetX = bench.x - 30; targetY = playerPen.y; break;
      case "right":  targetX = bench.x + bench.w + 30; targetY = playerPen.y; break;
      case "top":    targetX = playerPen.x; targetY = bench.y - 30; break;
      case "bottom": targetX = playerPen.x; targetY = bench.y + bench.h + 30; break;
    }
    // Aim at player but biased toward pushing them off the near edge
    const pushAngle = Math.atan2(targetY - aiPen.y, targetX - aiPen.x);
    const directAngle = Math.atan2(playerPen.y - aiPen.y, playerPen.x - aiPen.x);
    // Blend: mostly direct hit (which pushes them), slightly biased to edge
    const angle = lerpAngle(directAngle, pushAngle, 0.25);
    const dist = Math.hypot(playerPen.x - aiPen.x, playerPen.y - aiPen.y);
    const power = Math.min(cfg.powerMax, cfg.powerMin + (dist / bench.w) * 0.5 + 0.15);
    return { angle, power };
  }

  function computeBankShot(aiPen, playerPen, cfg) {
    // Find the best bumper to bank off of
    let bestAngle = Math.atan2(playerPen.y - aiPen.y, playerPen.x - aiPen.x);
    let bestScore = -Infinity;

    for (const bmp of engine.bumpers) {
      const bmpCenterX = bmp.x + bmp.w / 2;
      const bmpCenterY = bmp.y + bmp.h / 2;

      // Angle from AI pen to bumper
      const toBumperAngle = Math.atan2(bmpCenterY - aiPen.y, bmpCenterX - aiPen.x);
      const distToBumper = Math.hypot(bmpCenterX - aiPen.x, bmpCenterY - aiPen.y);

      // After bouncing off bumper, would it head toward player?
      const bumperToPlayer = Math.atan2(playerPen.y - bmpCenterY, playerPen.x - bmpCenterX);
      const distBumperToPlayer = Math.hypot(playerPen.x - bmpCenterX, playerPen.y - bmpCenterY);

      // Score: prefer bumpers that create a good ricochet angle
      const totalDist = distToBumper + distBumperToPlayer;
      const angleDiff = Math.abs(normalizeAngle(toBumperAngle - bumperToPlayer));
      // Good bank shots have a significant angle change (not straight through)
      const score = (angleDiff > 0.3 && angleDiff < 2.5) ? (1 / totalDist) * 1000 : 0;

      if (score > bestScore) {
        bestScore = score;
        bestAngle = toBumperAngle;
      }
    }

    // If no good bank shot found, fall back to direct
    if (bestScore <= 0) {
      bestAngle = Math.atan2(playerPen.y - aiPen.y, playerPen.x - aiPen.x);
    }

    const dist = Math.hypot(playerPen.x - aiPen.x, playerPen.y - aiPen.y);
    const power = Math.min(cfg.powerMax, cfg.powerMin + (dist / bench.w) * 0.45 + 0.1);
    return { angle: bestAngle, power };
  }

  function computePositioningAngle(aiPen, playerPen, cfg) {
    // Move toward center of table, but slightly offset from player
    const centerX = bench.x + bench.w / 2;
    const centerY = bench.y + bench.h / 2;
    // Offset toward center but perpendicular to player direction
    const toPlayerAngle = Math.atan2(playerPen.y - aiPen.y, playerPen.x - aiPen.x);
    const perpAngle = toPlayerAngle + (Math.random() > 0.5 ? Math.PI / 2 : -Math.PI / 2);
    const toCenterAngle = Math.atan2(centerY - aiPen.y, centerX - aiPen.x);
    return lerpAngle(toCenterAngle, perpAngle, 0.3);
  }

  function lerpAngle(a, b, t) {
    let diff = normalizeAngle(b - a);
    return a + diff * t;
  }

  function normalizeAngle(a) {
    while (a > Math.PI) a -= Math.PI * 2;
    while (a < -Math.PI) a += Math.PI * 2;
    return a;
  }

  function executeAITurn() {
    if (matchOver || roundOver || isTransitioningRound || currentTurn !== "p2") return;

    aiThinking = true;
    if (aiThinkingEl) aiThinkingEl.style.display = "flex";

    const cfg = AI_CONFIG[difficulty] || AI_CONFIG.normal;
    const thinkTime = cfg.thinkingTimeMin + Math.random() * (cfg.thinkingTimeMax - cfg.thinkingTimeMin);

    setTimeout(() => {
      if (matchOver || roundOver || isTransitioningRound) {
        aiThinking = false;
        if (aiThinkingEl) aiThinkingEl.style.display = "none";
        return;
      }

      const shot = aiAnalyzeAndShoot();
      if (!shot) {
        aiThinking = false;
        if (aiThinkingEl) aiThinkingEl.style.display = "none";
        return;
      }

      aiThinking = false;
      if (aiThinkingEl) aiThinkingEl.style.display = "none";

      engine.flick("p2", shot.angle, shot.power);
      pfAudio.flick();
      waitingForSettle = true;
    }, thinkTime);
  }

  // ================================================================
  // PLAYER CONTROLS (same as battle_local.js)
  // ================================================================

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
    if (matchOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving() || currentTurn !== "p1" || aiThinking) return;
    const powerNorm = parseInt(powerSlider.value, 10) / 100;
    if (powerNorm <= 0.04) return;
    const angleRad = (parseInt(angleSlider.value, 10) * Math.PI) / 180;

    engine.flick("p1", angleRad, powerNorm * (penPowerStat.p1 || 1));
    pfAudio.flick();
    waitingForSettle = true;

    powerSlider.value = 0;
    powerValText.textContent = "0%";
    powerQualText.textContent = "LOW";
  });

  // Canvas Drag Aiming (player only)
  function canvasPos(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width, scaleY = canvas.height / rect.height;
    const clientX = evt.touches ? evt.touches[0].clientX : evt.clientX;
    const clientY = evt.touches ? evt.touches[0].clientY : evt.clientY;
    return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
  }

  function startDrag(evt) {
    if (matchOver || roundOver || isTransitioningRound || waitingForSettle || engine.anyPenMoving() || currentTurn !== "p1" || aiThinking) return;
    const pos = canvasPos(evt);
    const pen = engine.pens["p1"];
    if (!pen) return;
    const dist = Math.hypot(pos.x - pen.x, pos.y - pen.y);
    if (dist > 75) return;
    dragging = { penId: "p1", anchorX: pen.x, anchorY: pen.y, mouseX: pos.x, mouseY: pos.y };
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
    const pen = engine.pens["p1"];

    if (pen && pen.alive && !engine.anyPenMoving() && !waitingForSettle && !roundOver && !matchOver && currentTurn === "p1" && !aiThinking) {
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

  // ================================================================
  // TURNS & ROUND LOGIC
  // ================================================================

  function handleSettle() {
    if (matchOver || roundOver || isTransitioningRound) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();

      // If it's now AI's turn, trigger AI after a short delay
      if (currentTurn === "p2" && !roundOver && !matchOver) {
        setTimeout(() => executeAITurn(), 300);
      }
    }
  }

  // Fallback settle check
  setInterval(() => {
    if (!matchOver && !roundOver && !isTransitioningRound && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = currentTurn === "p1" ? "p2" : "p1";
      updateTurnUI();

      if (currentTurn === "p2" && !roundOver && !matchOver) {
        setTimeout(() => executeAITurn(), 300);
      }
    }
  }, 200);

  function handleFall(penId) {
    if (roundOver || matchOver || isTransitioningRound) return;
    roundOver = true;
    isTransitioningRound = true;
    aiThinking = false;
    if (aiThinkingEl) aiThinkingEl.style.display = "none";
    pfAudio.fall();
    engine.screenShake(14);

    const winnerIsPlayer = penId === "p2"; // if p2 (AI) fell, player wins
    if (winnerIsPlayer) p1RoundWins++; else p2RoundWins++;
    updateScoreHUD();

    const winnerName = winnerIsPlayer ? p1Name : aiName;

    if (p1RoundWins >= 2 || p2RoundWins >= 2) {
      matchOver = true;
      showVictory(winnerIsPlayer ? "player1" : "player2");
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
          // If AI goes first, trigger it
          if (currentTurn === "p2") {
            setTimeout(() => executeAITurn(), 400);
          }
        }, 400);
      }
    };
    step();
  }

  function showVictory(winnerSlot) {
    const isPlayerWin = winnerSlot === "player1";
    const name = isPlayerWin ? p1Name : aiName;
    document.getElementById("victory-winner").textContent = `${name.toUpperCase()} WINS MATCH (${p1RoundWins} - ${p2RoundWins})`;

    if (isPlayerWin) {
      pfAudio.victory();
    } else {
      pfAudio.defeat();
    }

    // Report result to server (player always gets rewards for winning)
    fetch(window.PF_AI_RESULT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": window.PF_CSRF },
      body: JSON.stringify({ winner: winnerSlot, difficulty: difficulty }),
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
