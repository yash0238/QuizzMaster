// Team interface JavaScript with Socket.IO integration

let socket;
let gameId;
let teamCode;
let teamId;
let currentQuestionId;
const maskedOptions = new Set();
const lifelinesUsed = new Set();

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

  // Connection flow
  socket.on("connect", () => {
    if (gameId && teamCode) {
      socket.emit("join", { gameId, teamCode, role: "team" });
    }
  });

  socket.on("joined", () => {
    socket.emit("state_request", { gameId });
  });

  // State updates
  socket.on("state_update", (data) => {
    updateTeamDisplay(data);
    // Enable local lifelines during SHOW, disable otherwise
    if (data.state === "SHOW") {
      const phone = document.getElementById("phoneBtn");
      const discuss = document.getElementById("discussionBtn"); // match HTML id
      if (phone) { phone.disabled = false; phone.classList.remove("locked"); }
      if (discuss) { discuss.disabled = false; discuss.classList.remove("locked"); }
    } else {
      const phone = document.getElementById("phoneBtn");
      const discuss = document.getElementById("discussionBtn");
      if (phone) { phone.disabled = true; phone.classList.add("locked"); }
      if (discuss) { discuss.disabled = true; discuss.classList.add("locked"); }
    }
  });

  socket.on("error", (data) => {
    const msg = typeof data === "string" ? data : (data?.message || "Action rejected");
    showToast(msg, "warning");
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

  // 50-50 result (private to this team)
  socket.on("mask_applied", (data) => {
    if (data.questionId !== currentQuestionId) return;

    maskedOptions.clear();
    data.maskedOptions.forEach((i) => {
      maskedOptions.add(i);
      const btn = $(`[data-option="${i}"]`);
      if (btn) {
        btn.disabled = true;
        btn.classList.add("option-masked");
      }
    });
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

      // Debounce double-click
      buzzBtn.disabled = true;
      setTimeout(() => {
        if (!buzzBtn.classList.contains("buzz-locked")) {
          buzzBtn.disabled = false;
        }
      }, 900);
    });
    // Team Discussion (matches id="discussionBtn" in team.html)
    const discussionBtn = document.getElementById("discussionBtn");
    if (discussionBtn) {
      discussionBtn.addEventListener("click", () => {
        if (discussionBtn.disabled) return;
        discussionBtn.disabled = true;
        discussionBtn.classList.add("locked");
        showToast("Team Discussion used", "info");
      });
}

  }

  // Options (local selection only; no server submit in this MVP)
  $all(".option-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.dataset.option);
      if (Number.isNaN(i) || maskedOptions.has(i)) return;
      // Visual feedback for selection
      $all(".option-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
    });
  });

  // 50-50 lifeline
  const fifty = $("#fiftyFiftyBtn");
  if (fifty) {
    fifty.addEventListener("click", () => {
      if (fifty.disabled || lifelinesUsed.has("FIFTY_FIFTY") || !gameId || !teamCode) return;
      socket.emit("fifty_request", { gameId, teamCode });
      fifty.disabled = true;
      fifty.classList.add("lifeline-used");
      lifelinesUsed.add("FIFTY_FIFTY");
    });
  }

  // Manual lifelines (local-only)
  const phone = $("#phoneBtn");
  const discuss = $("#discussBtn");

  if (phone) {
    phone.addEventListener("click", () => {
      if (phone.disabled) return;
      lockAllLifelines();
      showToast("Phone‑a‑Friend used", "info");
    });
  }
  if (discuss) {
    discuss.addEventListener("click", () => {
      if (discuss.disabled) return;
      lockAllLifelines();
      showToast("Team Discussion used", "info");
    });
  }
}

function updateTeamDisplay(state) {
  // New question: reset buzz & options
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

  // Enable/disable by phase
  const buzzBtn = $("#buzzBtn");
  const fifty = $("#fiftyFiftyBtn");
  const show = state.state === "SHOW" && !!state.question;

  if (buzzBtn) buzzBtn.disabled = !show || buzzBtn.classList.contains("buzz-locked");

  if (fifty) {
    if (show && !lifelinesUsed.has("FIFTY_FIFTY") && state.question?.type === "MCQ") {
      fifty.disabled = false;
      fifty.classList.remove("locked");
    } else {
      fifty.disabled = true;
      fifty.classList.add("locked");
    }
  }
}

function unlockManualLifelines() {
  ["phoneBtn", "discussBtn"].forEach((id) => {
    const el = document.getElementById(id);
    if (el && !el.classList.contains("locked")) el.disabled = false;
  });
}

function lockManualLifelines() {
  ["phoneBtn", "discussBtn"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.disabled = true;
      el.classList.add("locked");
    }
  });
}

function lockAllLifelines() {
  ["fiftyFiftyBtn", "phoneBtn", "discussBtn"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.disabled = true;
      el.classList.add("locked");
    }
  });
}

// Init
document.addEventListener("DOMContentLoaded", initializeTeam);
