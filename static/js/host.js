// Host interface JavaScript with Socket.IO integration

let socket;
let gameId;
let timerInterval;

function initializeHost() {
    // Get initial state from page
    if (typeof initialState !== 'undefined') {
        gameId = initialState.gameId;
        updateHostDisplay(initialState);
    }
    
    // Connect to Socket.IO
    socket = connectSocket();
    
    // Socket event handlers
    socket.on('connect', () => {
        console.log('Host connected to server');
        if (gameId) {
            // Join game room as host
            socket.emit('join', {
                gameId: gameId,
                role: 'host'
            });
        }
    });
    
    socket.on('joined', (data) => {
        console.log('Host joined game:', data);
        // Request current state
        socket.emit('state_request', { gameId: gameId });
    });
    
    socket.on('state_update', (data) => {
        console.log('State update received:', data);
        updateHostDisplay(data);
    });
    
    socket.on('buzz_lock', (data) => {
        console.log('Buzz lock received:', data);
        showToast(`${data.winnerTeamName} buzzed in!`, 'success');
        
        // Update active team display
        const activeTeamElement = $('#activeTeam');
        if (activeTeamElement) {
            activeTeamElement.textContent = `Active Team: ${data.winnerTeamName}`;
            activeTeamElement.classList.add('active');
        }
    });
    
    socket.on('toast', (data) => {
        showToast(data.msg, 'info');
    });
    
    // Refresh button handler
    const refreshBtn = $('#refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            if (gameId && socket) {
                socket.emit('state_request', { gameId: gameId });
                showToast('Refreshing state...', 'info');
            }
        });
    }
}

function updateHostDisplay(state) {
    // Update state badge
    const stateBadge = $('#stateBadge');
    if (stateBadge) {
        stateBadge.textContent = state.state;
        stateBadge.className = `state-badge state-${state.state.toLowerCase()}`;
    }
    
    // Update timer
    updateTimer(state.deadlineEpochMs);
    
    // Update question display
    const questionText = $('#questionText');
    const optionsGrid = $('#optionsGrid');
    
    if (state.question && questionText && optionsGrid) {
        questionText.textContent = state.question.text;
        
        // Update options
        const optionElements = optionsGrid.children;
        const labels = ['A', 'B', 'C', 'D'];
        
        for (let i = 0; i < 4; i++) {
            if (optionElements[i] && state.question.options[i]) {
                optionElements[i].textContent = `${labels[i]}: ${state.question.options[i]}`;
                optionElements[i].classList.remove('correct');
            }
        }
    } else if (questionText && optionsGrid) {
        questionText.textContent = 'No question selected';
        
        const optionElements = optionsGrid.children;
        const labels = ['A', 'B', 'C', 'D'];
        
        for (let i = 0; i < 4; i++) {
            if (optionElements[i]) {
                optionElements[i].textContent = `${labels[i]}: Not available`;
                optionElements[i].classList.remove('correct');
            }
        }
    }
    
    // Update active team
    const activeTeamElement = $('#activeTeam');
    if (activeTeamElement) {
        if (state.activeTeamId) {
            activeTeamElement.textContent = `Active Team: ${state.activeTeamId}`;
            activeTeamElement.classList.add('active');
        } else {
            activeTeamElement.textContent = 'No team selected';
            activeTeamElement.classList.remove('active');
        }
    }
}

function updateTimer(deadlineEpochMs) {
    // Clear existing timer
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    
    const timerElement = $('#timer');
    if (!timerElement) return;
    
    if (!deadlineEpochMs || deadlineEpochMs <= 0) {
        timerElement.textContent = '--:--';
        timerElement.classList.remove('timer-warning', 'timer-danger');
        return;
    }
    
    // Start countdown timer
    timerInterval = setInterval(() => {
        const now = Date.now();
        const remaining = Math.max(0, deadlineEpochMs - now);
        
        if (remaining <= 0) {
            timerElement.textContent = '00:00';
            timerElement.classList.add('timer-danger');
            clearInterval(timerInterval);
            timerInterval = null;
            return;
        }
        
        const seconds = Math.ceil(remaining / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        const timeText = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        timerElement.textContent = timeText;
        
        // Apply warning/danger classes
        timerElement.classList.remove('timer-warning', 'timer-danger');
        if (seconds <= 10) {
            timerElement.classList.add('timer-danger');
        } else if (seconds <= 30) {
            timerElement.classList.add('timer-warning');
        }
    }, 100); // Update every 100ms for smooth countdown
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeHost);