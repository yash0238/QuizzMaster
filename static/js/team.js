// Team interface JavaScript with Socket.IO integration

let socket;
let gameId;
let teamCode;
let teamId;
let currentQuestionId;
let maskedOptions = new Set();
let lifelinesUsed = new Set();

function initializeTeam() {
    // Get team data from page
    if (typeof teamData !== 'undefined') {
        gameId = teamData.gameId;
        teamCode = teamData.teamCode;
        teamId = teamData.teamId;
        currentQuestionId = teamData.initialQuestionId;
    }
    
    // Connect to Socket.IO
    socket = connectSocket();
    
    // Socket event handlers
    socket.on('connect', () => {
        console.log('Team connected to server');
        if (gameId && teamCode) {
            // Join game and team rooms
            socket.emit('join', {
                gameId: gameId,
                teamCode: teamCode,
                role: 'team'
            });
        }
    });
    
    socket.on('joined', (data) => {
        console.log('Team joined:', data);
        // Request current state
        socket.emit('state_request', { gameId: gameId });
    });
    
    socket.on('state_update', (data) => {
        console.log('State update received:', data);
        updateTeamDisplay(data);
    });
    
    socket.on('buzz_lock', (data) => {
        console.log('Buzz lock received:', data);
        
        const buzzBtn = $('#buzzBtn');
        if (buzzBtn) {
            if (data.winnerTeamCode === teamCode) {
                // This team won the buzz
                buzzBtn.classList.add('buzz-winner');
                buzzBtn.querySelector('.buzz-text').textContent = 'YOU BUZZED!';
                showToast('You buzzed in first!', 'success');
            } else {
                // Another team won
                buzzBtn.disabled = true;
                buzzBtn.classList.add('buzz-locked');
                buzzBtn.querySelector('.buzz-text').textContent = 'LOCKED';
                showToast(`${data.winnerTeamCode} buzzed in first`, 'warning');
            }
        }
    });
    
    socket.on('mask_applied', (data) => {
        console.log('Mask applied:', data);
        
        if (data.questionId === currentQuestionId) {
            // Apply masks to options
            maskedOptions.clear();
            data.maskedOptions.forEach(optionIndex => {
                maskedOptions.add(optionIndex);
                const optionBtn = $(`[data-option="${optionIndex}"]`);
                if (optionBtn) {
                    optionBtn.disabled = true;
                    optionBtn.classList.add('option-masked');
                }
            });
            
            showToast('50-50 lifeline applied!', 'success');
        }
    });
    
    socket.on('toast', (data) => {
        showToast(data.msg, 'info');
    });
    
    // Setup event listeners
    setupTeamControls();
}

function setupTeamControls() {
    // Buzz button
    const buzzBtn = $('#buzzBtn');
    if (buzzBtn) {
        buzzBtn.addEventListener('click', () => {
            if (!buzzBtn.disabled && gameId && teamCode) {
                socket.emit('buzz', {
                    gameId: gameId,
                    teamCode: teamCode
                });
                
                // Temporarily disable to prevent double-clicks
                buzzBtn.disabled = true;
                setTimeout(() => {
                    if (!buzzBtn.classList.contains('buzz-locked')) {
                        buzzBtn.disabled = false;
                    }
                }, 1000);
            }
        });
    }
    
    // Option buttons (for future use - answer selection)
    $all('.option-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const optionIndex = parseInt(btn.dataset.option);
            if (!maskedOptions.has(optionIndex)) {
                // Handle option selection (if needed for answer submission)
                console.log('Option selected:', optionIndex);
            }
        });
    });
    
    // 50-50 lifeline button
    const fiftyFiftyBtn = $('#fiftyFiftyBtn');
    if (fiftyFiftyBtn) {
        fiftyFiftyBtn.addEventListener('click', () => {
            if (!fiftyFiftyBtn.disabled && !lifelinesUsed.has('FIFTY_FIFTY') && gameId && teamCode) {
                socket.emit('fifty_request', {
                    gameId: gameId,
                    teamCode: teamCode
                });
                
                // Lock the lifeline
                fiftyFiftyBtn.disabled = true;
                fiftyFiftyBtn.classList.add('lifeline-used');
                lifelinesUsed.add('FIFTY_FIFTY');
            }
        });
    }
    
    // Other lifeline buttons (placeholder for future implementation)
    const phoneBtn = $('#phoneBtn');
    const discussionBtn = $('#discussionBtn');
    
    if (phoneBtn) {
        phoneBtn.addEventListener('click', () => {
            showToast('Phone-a-Friend lifeline not yet implemented', 'info');
        });
    }
    
    if (discussionBtn) {
        discussionBtn.addEventListener('click', () => {
            showToast('Team Discussion lifeline not yet implemented', 'info');
        });
    }
}

function updateTeamDisplay(state) {
    // Update question if changed
    if (state.question && state.question.id !== currentQuestionId) {
        currentQuestionId = state.question.id;
        maskedOptions.clear(); // Clear masks for new question
        
        // Reset buzz button for new question
        const buzzBtn = $('#buzzBtn');
        if (buzzBtn) {
            buzzBtn.disabled = false;
            buzzBtn.classList.remove('buzz-winner', 'buzz-locked');
            buzzBtn.querySelector('.buzz-text').textContent = 'BUZZ!';
        }
        
        // Reset options
        $all('.option-btn').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('option-masked');
        });
    }
    
    // Update options display
    if (state.question) {
        const optionBtns = $all('.option-btn');
        const labels = ['A', 'B', 'C', 'D'];
        
        for (let i = 0; i < 4; i++) {
            if (optionBtns[i] && state.question.options[i]) {
                optionBtns[i].textContent = `${labels[i]}: ${state.question.options[i]}`;
                
                // Reapply masks if they exist
                if (maskedOptions.has(i)) {
                    optionBtns[i].disabled = true;
                    optionBtns[i].classList.add('option-masked');
                }
            }
        }
    }
    
    // Enable/disable controls based on state
    const buzzBtn = $('#buzzBtn');
    const fiftyFiftyBtn = $('#fiftyFiftyBtn');
    
    if (state.state === 'SHOW' && state.question) {
        // Enable buzz button if no winner yet and not locked
        if (buzzBtn && !buzzBtn.classList.contains('buzz-locked')) {
            buzzBtn.disabled = false;
        }
        
        // Enable 50-50 if not used and question is MCQ
        if (fiftyFiftyBtn && !lifelinesUsed.has('FIFTY_FIFTY') && state.question.type === 'MCQ') {
            fiftyFiftyBtn.disabled = false;
            fiftyFiftyBtn.classList.remove('locked');
        }
    } else {
        // Disable controls for other states
        if (buzzBtn) {
            buzzBtn.disabled = true;
        }
        
        if (fiftyFiftyBtn) {
            fiftyFiftyBtn.disabled = true;
            fiftyFiftyBtn.classList.add('locked');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTeam);