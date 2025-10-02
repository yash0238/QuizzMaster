// Team interface JavaScript with Socket.IO integration

let socket;
let gameId;
let teamCode;
let teamId;
let currentQuestionId;

let currentRoundId = null;                // Track the active round (sent by server)
const maskedOptions = new Set();          // Indices 0..3 masked by 50-50
const lifelinesUsedByRound = new Map();   // Map<roundId, Set<"FIFTY_FIFTY"|"PHONE"|"DISCUSS">>

function markLifelineUsed(key) {
  if (!currentRoundId) return;
  if (!lifelinesUsedByRound.has(currentRoundId)) lifelinesUsedByRound.set(currentRoundId, new Set());
  lifelinesUsedByRound.get(currentRoundId).add(key);
}

function isUsedThisRound(key) {
  return currentRoundId && lifelinesUsedByRound.get(currentRoundId)?.has(key);
}

function initializeTeam() {
  // Bootstrap from template
  if (typeof teamData !== "undefined") {
    gameId = teamData.gameId;
    teamCode = teamData.teamCode;
    teamId = teamData.teamId;
    currentQuestionId = teamData.initialQuestionId;
  }

  // Connect Socket.IO
  socket = connectSocket();
  if (!socket) {
    console.warn("Socket unavailable");
    return;
  }

  // Join game/team rooms
  socket.on("connect", () => {
    if (gameId && teamCode) socket.emit("join", { gameId, teamCode, role: "team" });
  });

  socket.on("joined", () => {
    socket.emit("state_request", { gameId });
  });

  // State updates from server
  socket.on("state_update", (data) => {
    // Track round change
    const incomingRoundId = data.currentRoundId ?? currentRoundId;
    const roundChanged = currentRoundId !== incomingRoundId;
    currentRoundId = incomingRoundId;

    updateTeamDisplay(data);

    // If round changed, clear local locks so buttons can be re-evaluated
    if (roundChanged) {
      ["fiftyFiftyBtn", "phoneBtn", "discussionBtn"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) { el.classList.remove("locked"); el.disabled = false; }
      });
    }

    // Enable/disable by state and per-round usage
    const inShow = data.state === "SHOW";
    const fifty = document.getElementById("fiftyFiftyBtn");
    if (fifty) {
      if (inShow && data.question?.type === "MCQ" && !isUsedThisRound("FIFTY_FIFTY")) {
        fifty.disabled = false; fifty.classList.remove("locked");
      } else {
        fifty.disabled = true; fifty.classList.add("locked");
      }
    }

    const phone = document.getElementById("phoneBtn");
    if (phone) {
      if (inShow && !isUsedThisRound("PHONE")) {
        phone.disabled = false; phone.classList.remove("locked");
      } else {
        phone.disabled = true; phone.classList.add("locked");
      }
    }

    const discuss = document.getElementById("discussionBtn");
    if (discuss) {
      if (inShow && !isUsedThisRound("DISCUSS")) {
        discuss.disabled = false; discuss.classList.remove("locked");
      } else {
        discuss.disabled = true; discuss.classList.add("locked");
      }
    }
  });

  // Show server rejections
  socket.on("error", (data) => {
    const msg = typeof data === "string" ? data : (data?.message || "Action rejected");
    showToast(msg, "warning");
    // If server says lifeline already used, hard-lock button this round
    if (String(msg).toLowerCase().includes("already used")) {
      markLifelineUsed("FIFTY_FIFTY");
      const b = document.getElementById("fiftyFiftyBtn");
      if (b) { b.disabled = true; b.classList.add("locked"); }
    }
  });

  // Buzz race result
  socket.on("buzz_lock", (data) => {
    const buzzBtn = $("#buzzBtn");
    if (!buzzBtn) return;
    if (data.winnerTeamCode === teamCode) {
      buzzBtn.classList.add("buzz-winner");
      const label = buzzBtn.querySelector(".buzz-text");
      if (label) label.textContent = "YOU BUZZED!";
      showToast("You buzzed in first!", "success");
    } else {
      buzzBtn.disabled = true;
      buzzBtn.classList.add("buzz-locked");
      const label = buzzBtn.querySelector(".buzz-text");
      if (label) label.textContent = "LOCKED";
      showToast(`${data.winnerTeamCode} buzzed in first`, "warning");
    }
  });

  // 50-50 result (private to this team) - tolerant payload
  socket.on("mask_applied", (data) => {
    const indices = data?.maskedOptions ?? data?.masked_indices ?? data?.indices ?? [];
    if (data?.questionId && currentQuestionId && data.questionId !== currentQuestionId) return;
    if (!Array.isArray(indices) || indices.length === 0) {
      showToast("50‑50 data missing", "warning");
      return;
    }
    maskedOptions.clear();
    indices.forEach((i) => {
      maskedOptions.add(i);
      const btn = document.querySelector(`[data-option="${i}"]`);
      if (btn) {
        btn.disabled = true;
        btn.classList.add("option-masked");
      }
    });
    markLifelineUsed("FIFTY_FIFTY"); // lock for rest of the round
    showToast("50-50 lifeline applied!", "success");
  });

  // Toasts
  socket.on("toast", (data) => showToast(data.msg, "info"));

  // Wire UI controls
  setupTeamControls();
}

function setupTeamControls() {
  // Buzz
  const buzzBtn = $("#buzzBtn");
  if (buzzBtn) {
    buzzBtn.addEventListener("click", () => {
      if (buzzBtn.disabled || !gameId || !teamCode) return;
      socket.emit("buzz", { gameId, teamCode });
      buzzBtn.disabled = true;
      setTimeout(() => {
        if (!buzzBtn.classList.contains("buzz-locked")) buzzBtn.disabled = false;
      }, 900);
    });
  }

  // Options (local highlight only)
  $all(".option-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.dataset.option);
      if (Number.isNaN(i) || maskedOptions.has(i)) return;
      $all(".option-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
    });
  });

  // 50-50 lifeline (optimistic lock, server confirms)
  const fifty = $("#fiftyFiftyBtn");
  if (fifty) {
    fifty.addEventListener("click", () => {
      if (fifty.disabled || !gameId || !teamCode || isUsedThisRound("FIFTY_FIFTY")) return;
      socket.emit("fifty_request", { gameId, teamCode });
      fifty.disabled = true;
      fifty.classList.add("lifeline-used");
    });
  }

  // Phone-a-Friend (local-only)
  const phone = document.getElementById("phoneBtn");
  if (phone) {
    phone.addEventListener("click", () => {
      if (phone.disabled || isUsedThisRound("PHONE")) return;
      markLifelineUsed("PHONE");
      phone.disabled = true;
      phone.classList.add("locked");
      showToast("Phone‑a‑Friend used", "info");
    });
  }

  // Team Discussion (local-only; id matches template)
  const discussionBtn = document.getElementById("discussionBtn");
  if (discussionBtn) {
    discussionBtn.addEventListener("click", () => {
      if (discussionBtn.disabled || isUsedThisRound("DISCUSS")) return;
      markLifelineUsed("DISCUSS");
      discussionBtn.disabled = true;
      discussionBtn.classList.add("locked");
      showToast("Team Discussion used", "info");
    });
  }
}

function updateTeamDisplay(state) {
  // New question: reset buzz & options (lifeline usage is per-round, not cleared here)
  if (state.question && state.question.id !== currentQuestionId) {
    currentQuestionId = state.question.id;
    maskedOptions.clear();

    const buzzBtn = $("#buzzBtn");
    if (buzzBtn) {
      buzzBtn.disabled = false;
      buzzBtn.classList.remove("buzz-winner", "buzz-locked");
      const label = buzzBtn.querySelector(".buzz-text");
      if (label) label.textContent = "BUZZ!";
    }

    $all(".option-btn").forEach((btn) => {
      btn.disabled = false;
      btn.classList.remove("option-masked", "selected");
    });
  }

  // Update option texts and reapply masks
  if (state.question) {
    const labels = ["A", "B", "C", "D"];
    $all(".option-btn").forEach((btn, i) => {
      if (!state.question.options[i]) return;
      btn.textContent = `${labels[i]}: ${state.question.options[i]}`;
      if (maskedOptions.has(i)) {
        btn.disabled = true;
        btn.classList.add("option-masked");
      }
    });
  }

  // Buzz enablement by phase
  const buzzBtn = $("#buzzBtn");
  const inShow = state.state === "SHOW" && !!state.question;
  if (buzzBtn) buzzBtn.disabled = !inShow || buzzBtn.classList.contains("buzz-locked");
}

// Init
document.addEventListener("DOMContentLoaded", initializeTeam);
