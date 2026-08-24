/* PenFight Arena — Online Battle Controller
   Wraps PenFightEngine with a WebSocket connection to the BattleConsumer.
   Physics run identically on both peers (no gameplay-relevant randomness —
   see engine.js); the WS relay just replays the same flick inputs on both
   screens so they land in the same place. Win/reward resolution is always
   confirmed by the server's "match_over" broadcast, never decided locally. */
(() => {
  const canvas = document.getElementById("battle-canvas");
  const mySlot = window.PF_MY_SLOT; // "player1" (host) or "player2" (guest)
  const opponentSlot = mySlot === "player1" ? "player2" : "player1";

  const penConfig = {
    player1: window.PF_HOST_PEN,
    player2: window.PF_GUEST_PEN,
  };
  const nameFor = { player1: window.PF_HOST_NAME, player2: window.PF_GUEST_NAME };
  const penIdFor = { player1: window.PF_HOST_PEN.penId, player2: window.PF_GUEST_PEN.penId };
  const skinIdFor = { player1: window.PF_HOST_PEN.skinId, player2: window.PF_GUEST_PEN.skinId };

  canvas.style.background = `linear-gradient(135deg, ${window.PF_ARENA.fromColor}, ${window.PF_ARENA.toColor})`;

  const bench = { x: 140, y: 130, w: 620, h: 160 };
  const engine = new PenFightEngine(canvas, {
    bench,
    onSettle: handleSettle,
    onFall: handleFall,
    onCollision: (a, b, strength) => { pfAudio.collision(strength); engine.screenShake(4 + strength * 10); },
  });
  engine.benchColorLight = shade(window.PF_ARENA.benchColor, 24);
  engine.benchColorDark = shade(window.PF_ARENA.benchColor, -30);

  engine.addPen("player1", {
    x: bench.x + bench.w * 0.28, y: bench.y + bench.h / 2, angle: 0,
    color: penConfig.player1.color, accent: penConfig.player1.accent,
    trailColor: penConfig.player1.trail, glow: !!penConfig.player1.glow,
    mass: penConfig.player1.mass || 1, friction: penConfig.player1.friction || 1,
    assetKey: penConfig.player1.assetKey || "classic-blue"
  });
  engine.addPen("player2", {
    x: bench.x + bench.w * 0.72, y: bench.y + bench.h / 2, angle: Math.PI,
    color: penConfig.player2.color, accent: penConfig.player2.accent,
    trailColor: penConfig.player2.trail, glow: !!penConfig.player2.glow,
    mass: penConfig.player2.mass || 1, friction: penConfig.player2.friction || 1,
    assetKey: penConfig.player2.assetKey || "sunset-blaze"
  });

  let currentTurn = "player1";
  let gameOver = false;
  let waitingForSettle = false;
  let dragging = null;
  let connected = false;

  const turnBanner = document.getElementById("turn-banner");
  const powerFill = document.getElementById("power-fill");
  const powerLabel = document.getElementById("power-label");
  const hintText = document.getElementById("hint-text");
  const connPill = document.getElementById("conn-pill");
  const sfxToggle = document.getElementById("sfx-toggle");
  sfxToggle.addEventListener("click", () => {
    pfAudio.setSfx(!pfAudio.sfxOn);
    sfxToggle.textContent = pfAudio.sfxOn ? "🔊 SFX" : "🔇 SFX";
  });
  const MAX_PULL = 95;

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
    runCountdown();
  });
  socket.addEventListener("close", () => {
    connPill.textContent = "Disconnected";
    connPill.classList.remove("ok"); connPill.classList.add("bad");
  });

  socket.addEventListener("message", (evt) => {
    const data = JSON.parse(evt.data);
    if (data.kind === "flick" && data.slot !== mySlot) {
      // Opponent flicked their own pen on their screen — replay identically here.
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
    if (gameOver || waitingForSettle || engine.anyPenMoving() || currentTurn !== mySlot) return;
    const pos = canvasPos(evt);
    const pen = engine.pens[mySlot];
    if (!pen) return;
    const dist = Math.hypot(pos.x - pen.x, pos.y - pen.y);
    if (dist > 70) return;
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
    if (gameOver) return;
    if (!engine.anyPenMoving() && waitingForSettle) {
      waitingForSettle = false;
      currentTurn = currentTurn === "player1" ? "player2" : "player1";
      updateTurnUI();
    }
  }
  setInterval(() => {
    if (!gameOver && waitingForSettle && !engine.anyPenMoving()) {
      waitingForSettle = false;
      currentTurn = currentTurn === "player1" ? "player2" : "player1";
      updateTurnUI();
    }
  }, 200);

  function handleFall(penId) {
    if (gameOver) return;
    gameOver = true;
    pfAudio.fall();
    engine.screenShake(14);
    // Report the authoritative "pen fell" event. The server decides the
    // rest (winner, rewards, XP, achievements) — see multiplayer.services.
    send({
      kind: "pen_out", slot: penId,
      pen_ids: {
        player1_pen: penIdFor.player1, player1_skin: skinIdFor.player1,
        player2_pen: penIdFor.player2, player2_skin: skinIdFor.player2,
      },
    });
  }

  function handleMatchOver(data) {
    gameOver = true;
    const iWon = data.winner_slot === mySlot;
    document.getElementById("victory-winner").textContent = `${data.winner_username.toUpperCase()} WINS`;
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
    setTimeout(() => { document.getElementById("victory-overlay").style.display = "flex"; }, 300);
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
      if (seq[i] === "FIGHT!") { pfAudio.fight(); text.style.color = "#34d399"; } else { pfAudio.countdownTick(); }
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
})();
