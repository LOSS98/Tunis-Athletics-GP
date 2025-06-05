// manage_results.js - Version complète avec High Jump
let searchTimeout;
let currentResultId = null;

// Configuration avec valeurs par défaut
const isFieldEvent = window.isFieldEvent || false;
const isTrackEvent = window.isTrackEvent || false;
const gameEvent = window.gameEvent || '';
const hasWpaPoints = window.hasWpaPoints || false;
const specialValues = window.specialValues || ['DNS', 'DNF', 'DQ', 'NM', 'X', 'O', '-'];
const gameId = window.gameId;

// Utilitaires
function getCSRFToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity ${
        type === 'success' ? 'bg-green-500 text-white' : 
        type === 'error' ? 'bg-red-500 text-white' : 
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function setLoadingState(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        button.disabled = true;
    } else {
        button.innerHTML = button.dataset.originalText;
        button.disabled = false;
    }
}

// Recherche d'athlètes
function initializeAthleteSearch() {
    const athleteSearch = document.getElementById('athleteSearch');
    const athleteResults = document.getElementById('athleteResults');

    if (!athleteSearch || !athleteResults) return;

    athleteSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            athleteResults.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/admin/athletes/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(athletes => {
                    athleteResults.innerHTML = '';
                    if (athletes.length === 0) {
                        athleteResults.innerHTML = '<div class="p-2 text-gray-500">No athletes found</div>';
                    } else {
                        athletes.forEach(athlete => {
                            const div = document.createElement('div');
                            div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';
                            div.innerHTML = `
                                <div class="flex justify-between items-center">
                                    <div>
                                        <strong>${athlete.sdms}</strong> - ${athlete.name} (${athlete.country})
                                    </div>
                                    <div class="text-right">
                                        <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${athlete.class}</span>
                                        <div class="text-xs text-gray-500 mt-1">${athlete.gender}</div>
                                    </div>
                                </div>
                            `;
                            div.onclick = () => selectAthlete(athlete);
                            athleteResults.appendChild(div);
                        });
                    }
                    athleteResults.classList.remove('hidden');
                })
                .catch(error => {
                    console.error('Search error:', error);
                    athleteResults.innerHTML = '<div class="p-2 text-red-500">Search failed</div>';
                    athleteResults.classList.remove('hidden');
                });
        }, 300);
    });
}

function initializeGuideSearch() {
    const guideSearch = document.getElementById('guideSearch');
    const guideResults = document.getElementById('guideResults');

    if (!guideSearch || !guideResults) return;

    guideSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            guideResults.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/admin/athletes/search?q=${encodeURIComponent(query)}&guides=1`)
                .then(response => response.json())
                .then(athletes => {
                    guideResults.innerHTML = '';
                    if (athletes.length === 0) {
                        guideResults.innerHTML = '<div class="p-2 text-gray-500">No athletes found</div>';
                    } else {
                        athletes.forEach(athlete => {
                            const div = document.createElement('div');
                            div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';
                            div.innerHTML = `<strong>${athlete.sdms}</strong> - ${athlete.name} (${athlete.country})`;
                            div.onclick = () => selectGuide(athlete);
                            guideResults.appendChild(div);
                        });
                    }
                    guideResults.classList.remove('hidden');
                });
        }, 300);
    });
}

function selectAthlete(athlete) {
    const selectedSdms = document.getElementById('selectedSdms');
    const athleteSearch = document.getElementById('athleteSearch');
    const athleteResults = document.getElementById('athleteResults');
    const selectedAthlete = document.getElementById('selectedAthlete');
    const selectedGuideSdms = document.getElementById('selectedGuideSdms');
    const selectedGuide = document.getElementById('selectedGuide');

    if (selectedSdms) selectedSdms.value = athlete.sdms;
    if (athleteSearch) athleteSearch.value = '';
    if (athleteResults) athleteResults.classList.add('hidden');
    if (selectedAthlete) selectedAthlete.innerHTML = `Selected: <strong>${athlete.sdms}</strong> - ${athlete.name}`;
    if (selectedGuideSdms) selectedGuideSdms.value = '';
    if (selectedGuide) selectedGuide.innerHTML = '';
}

function selectFromStartList(sdms, name, gender, athleteClass, guideSdms) {
    const athlete = { sdms: sdms, name: name, gender: gender, class: athleteClass };
    selectAthlete(athlete);
    if (guideSdms) {
        const selectedGuideSdms = document.getElementById('selectedGuideSdms');
        const selectedGuide = document.getElementById('selectedGuide');
        if (selectedGuideSdms) selectedGuideSdms.value = guideSdms;
        if (selectedGuide) selectedGuide.innerHTML = `Guide SDMS: <strong>${guideSdms}</strong>`;
    }

function selectGuide(athlete) {
    const sdmsInput = document.getElementById('selectedGuideSdms') || document.getElementById('editGuideSdms');
    const searchInput = document.getElementById('guideSearch') || document.getElementById('editGuideSearch');
    const resultsDiv = document.getElementById('guideResults') || document.getElementById('editGuideResults');
    const displayDiv = document.getElementById('selectedGuide') || document.getElementById('editSelectedGuide');

    if (sdmsInput) sdmsInput.value = athlete.sdms;
    if (searchInput) searchInput.value = '';
    if (resultsDiv) resultsDiv.classList.add('hidden');
    if (displayDiv) displayDiv.innerHTML = `Guide: <strong>${athlete.sdms}</strong> - ${athlete.name}`;
}

function selectSpecialValue(value) {
    const performanceInput = document.getElementById('performanceValue');
    if (performanceInput && value) {
        performanceInput.value = value;
    }
}

// Actions de jeu
function togglePublish(gameIdParam, event) {
    const button = event.target.closest('button');
    setLoadingState(button, true);

    fetch(`/admin/games/${gameIdParam}/publish`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification('Error: ' + data.error, 'error');
            setLoadingState(button, false);
        } else {
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating publish status', 'error');
        setLoadingState(button, false);
    });
}

function autoRankResults(gameIdParam, event) {
    if (confirm('Auto-rank all results? This will update ranks automatically.')) {
        const button = event.target.closest('button');
        setLoadingState(button, true);

        fetch(`/admin/games/${gameIdParam}/auto-rank`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Results auto-ranked successfully!', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                setLoadingState(button, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error auto-ranking results', 'error');
            setLoadingState(button, false);
        });
    }
}

function selectFinalistsRound1(gameIdParam) {
    if (confirm('Select finalists for final round based on qualifying attempts?')) {
        fetch(`/admin/games/${gameIdParam}/auto-rank-round1`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error selecting finalists', 'error');
        });
    }
}

function recalculateRaza(gameIdParam) {
    if (confirm('Recalculate all RAZA scores?')) {
        const button = event.target;
        setLoadingState(button, true);

        fetch(`/admin/games/${gameIdParam}/recalculate-raza`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`RAZA scores recalculated! Updated ${data.updated} results.`, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                setLoadingState(button, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error recalculating RAZA scores', 'error');
            setLoadingState(button, false);
        });
    }
}

function openGameEditModalFromGlobal(gameId) {
    if (window.gameEditData) {
        openGameEditModal(gameId, window.gameEditData);
    } else {
        showNotification('Game data not found', 'error');
    }
}

// Modal d'édition de jeu
function openGameEditModal(gameIdParam, gameData) {
    const modal = document.getElementById('gameEditModal');

    if (!modal) {
        showNotification('Game edit modal not found', 'error');
        return;
    }

    // Remplir les champs
    const fields = {
        'editGameId': gameIdParam,
        'editEvent': gameData.event,
        'editGender': gameData.gender,
        'editClasses': gameData.classes,
        'editPhase': gameData.phase || '',
        'editArea': gameData.area || '',
        'editDay': gameData.day,
        'editTime': gameData.time,
        'editNbAthletes': gameData.nb_athletes,
        'editStatus': gameData.status
    };

    Object.entries(fields).forEach(([fieldId, value]) => {
        const field = document.getElementById(fieldId);
        if (field) field.value = value;
    });

    const publishedCheckbox = document.getElementById('editPublished');
    const wpaPointsCheckbox = document.getElementById('editWpaPoints');

    if (publishedCheckbox) publishedCheckbox.checked = gameData.published || false;
    if (wpaPointsCheckbox) wpaPointsCheckbox.checked = gameData.wpa_points || false;

    modal.classList.remove('hidden');
}

function closeGameEditModal() {
    const modal = document.getElementById('gameEditModal');
    if (modal) modal.classList.add('hidden');
}

function editAttemptsFromGlobal(resultId) {
    const resultData = window[`resultEditData_${resultId}`];
    if (resultData) {
        editAttempts(resultId, resultData);
    } else {
        showNotification('Result data not found', 'error');
    }
}

function editAttempts(resultId, resultData) {
    const modal = document.getElementById('editAttemptsModal');
    if (!modal) {
        showNotification('Edit attempts modal not found', 'error');
        return;
    }

    currentResultId = resultId;
    document.getElementById('editResultId').value = resultId;

    // Remplir les champs des tentatives si elles existent
    if (resultData.attempts) {
        if (gameEvent === 'High Jump') {
            // High Jump specific: créer l'interface dynamiquement
            createHighJumpEditInterface(resultData.attempts);
        } else {
            // Other field events
            resultData.attempts.forEach((attempt, index) => {
                const attemptInput = document.getElementById(`editAttempt${index + 1}`);
                if (attemptInput && attempt.value) {
                    attemptInput.value = attempt.value;
                }

                // Remplir le vent si applicable
                const windInput = document.getElementById(`editWind${index + 1}`);
                if (windInput && attempt.wind_velocity) {
                    windInput.value = attempt.wind_velocity;
                }
            });
        }
    }

    // Remplir les autres champs
    const weightInput = document.getElementById('editWeight');
    if (weightInput && resultData.weight) {
        weightInput.value = resultData.weight;
    }

    const guideInput = document.getElementById('editGuideSdms');
    const guideDisplay = document.getElementById('editSelectedGuide');
    if (guideInput) guideInput.value = resultData.guide_sdms || '';
    if (guideDisplay) {
        if (resultData.guide_sdms) {
            guideDisplay.innerHTML = `Guide SDMS: <strong>${resultData.guide_sdms}</strong>`;
        } else {
            guideDisplay.innerHTML = '';
        }
    }

    const recordSelect = document.getElementById('editRecord');
    if (recordSelect && resultData.record) {
        recordSelect.value = resultData.record;
    }

    modal.classList.remove('hidden');
}

function createHighJumpEditInterface(attempts) {
    const container = document.getElementById('highJumpAttemptsContainer');
    if (!container) {
        console.warn('High Jump attempts container not found');
        return;
    }

    // Vider le conteneur
    container.innerHTML = '';

    // Créer les champs pour les tentatives existantes
    attempts.forEach((attempt, index) => {
        const attemptDiv = document.createElement('div');
        attemptDiv.className = 'border rounded p-3 bg-white shadow-sm';
        attemptDiv.innerHTML = `
            <label class="text-sm font-medium mb-1 block text-purple-700">
                Attempt ${index + 1}
            </label>
            <div class="flex gap-2">
                <input type="number" step="0.01" id="editHeight${index + 1}"
                       class="w-24 px-2 py-2 border rounded-lg focus:outline-none focus:border-purple-500"
                       placeholder="1.85" value="${attempt.height || ''}">
                <select id="editAttempt${index + 1}"
                        class="flex-1 px-2 py-2 border rounded-lg focus:outline-none focus:border-purple-500">
                    <option value="">-</option>
                    <option value="O" ${attempt.value === 'O' ? 'selected' : ''}>O (Success)</option>
                    <option value="X" ${attempt.value === 'X' ? 'selected' : ''}>X (Failure)</option>
                    <option value="-" ${attempt.value === '-' ? 'selected' : ''}>- (Pass)</option>
                    <option value="XO" ${attempt.value === 'XO' ? 'selected' : ''}>XO</option>
                    <option value="XXO" ${attempt.value === 'XXO' ? 'selected' : ''}>XXO</option>
                    <option value="XXX" ${attempt.value === 'XXX' ? 'selected' : ''}>XXX (Elimination)</option>
                </select>
            </div>
        `;
        container.appendChild(attemptDiv);
    });

    // Ajouter un champ vide pour une nouvelle tentative
    const newAttemptDiv = document.createElement('div');
    newAttemptDiv.className = 'border-2 border-dashed border-purple-300 rounded p-3 bg-purple-50';
    newAttemptDiv.innerHTML = `
        <label class="text-sm font-medium mb-1 block text-purple-600">
            <i class="fas fa-plus mr-1"></i>Add New Attempt
        </label>
        <div class="flex gap-2">
            <input type="number" step="0.01" id="editHeight${attempts.length + 1}"
                   class="w-24 px-2 py-2 border rounded-lg focus:outline-none focus:border-purple-500"
                   placeholder="1.85">
            <select id="editAttempt${attempts.length + 1}"
                    class="flex-1 px-2 py-2 border rounded-lg focus:outline-none focus:border-purple-500">
                <option value="">-</option>
                <option value="O">O (Success)</option>
                <option value="X">X (Failure)</option>
                <option value="-">- (Pass)</option>
                <option value="XO">XO</option>
                <option value="XXO">XXO</option>
                <option value="XXX">XXX (Elimination)</option>
            </select>
        </div>
    `;
    container.appendChild(newAttemptDiv);
}

function closeEditAttemptsModal() {
    const modal = document.getElementById('editAttemptsModal');
    if (modal) {
        modal.classList.add('hidden');
        currentResultId = null;
    }
}

// Autres fonctions
function toggleAttempts(resultId) {
    const attemptsDiv = document.getElementById(`attempts-${resultId}`);
    const icon = document.getElementById(`attempts-icon-${resultId}`);

    if (attemptsDiv && icon) {
        if (attemptsDiv.classList.contains('hidden')) {
            attemptsDiv.classList.remove('hidden');
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            attemptsDiv.classList.add('hidden');
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

function deleteResult(resultId) {
    if (confirm('Delete this result?')) {
        const formData = new FormData();
        formData.append('csrf_token', getCSRFToken());

        fetch(`/admin/results/${resultId}/delete`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                const row = document.querySelector(`tr[data-result-id="${resultId}"]`);
                if (row) row.remove();
                showNotification('Result deleted successfully', 'success');
            } else {
                showNotification('Error deleting result', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error deleting result', 'error');
        });
    }
}

// High Jump Modal pour ajouter des tentatives
function showAddAttemptModal(resultId) {
    currentResultId = resultId;
    const modal = document.getElementById('addAttemptModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closeAddAttemptModal() {
    const modal = document.getElementById('addAttemptModal');
    if (modal) {
        modal.classList.add('hidden');
        currentResultId = null;
    }
}

function addHighJumpAttempt() {
    if (!currentResultId) {
        showNotification('No result selected', 'error');
        return;
    }

    const height = document.getElementById('attemptHeight').value;
    const result = document.getElementById('attemptResult').value;

    if (!height || !result) {
        showNotification('Height and result are required', 'error');
        return;
    }

    const data = {
        height: parseFloat(height),
        result: result
    };

    fetch(`/admin/results/${currentResultId}/add-attempt`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeAddAttemptModal();
            showNotification('Attempt added successfully!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding attempt', 'error');
    });
}

// Drag and Drop
function initializeDragAndDrop() {
    const tbody = document.getElementById('sortableResults');
    if (!tbody) return;

    new Sortable(tbody, {
        animation: 150,
        ghostClass: 'sortable-ghost',
        onEnd: function(evt) {
            updateManualRanking();
        }
    });
}

function updateManualRanking() {
    if (!gameId) {
        showNotification('Game ID not found', 'error');
        return;
    }

    const rows = document.querySelectorAll('#sortableResults .draggable-row');
    const rankings = [];

    rows.forEach((row, index) => {
        const resultId = row.dataset.resultId;
        const newRank = index + 1;
        rankings.push({ result_id: resultId, rank: newRank });

        // Update visual rank
        const rankCell = row.querySelector('td:nth-child(2) span:last-child');
        if (rankCell) rankCell.textContent = newRank;
    });

    fetch(`/admin/games/${gameId}/update-manual-ranking`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ rankings: rankings })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Rankings updated', 'success');
        } else {
            showNotification('Error updating rankings', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating rankings', 'error');
    });
}
function recalculateHighJump(gameIdParam) {
    if (confirm('Recalculate High Jump ranking with proper tie-breaking rules?')) {
        const button = event.target;
        setLoadingState(button, true);

        fetch(`/admin/games/${gameIdParam}/recalculate-high-jump`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('High Jump ranking recalculated successfully!', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                setLoadingState(button, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error recalculating High Jump ranking', 'error');
            setLoadingState(button, false);
        });
    }
}
function toggleGameOfficial(gameId) {
    const confirmMessage = 'Are you sure you want to change the official status of this entire game and ALL its results?';
    if (!confirm(confirmMessage)) {
        return;
    }

    const button = event.target.closest('button');
    setLoadingState(button, true);

    fetch(`/admin/games/${gameId}/toggle-official`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
            setLoadingState(button, false);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error changing official status', 'error');
        setLoadingState(button, false);
    });
}
// Form handlers
function initializeFormHandlers() {
    const gameEditForm = document.getElementById('gameEditForm');
    if (gameEditForm) {
        gameEditForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const gameIdValue = document.getElementById('editGameId').value;

            fetch(`/admin/games/${gameIdValue}/edit`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCSRFToken() },
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    closeGameEditModal();
                    showNotification('Game updated successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification('Error updating game', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error updating game', 'error');
            });
        });
    }

    // Gestionnaire pour le formulaire d'édition des tentatives
    const editAttemptsForm = document.getElementById('editAttemptsForm');
    if (editAttemptsForm) {
        editAttemptsForm.addEventListener('submit', function(e) {
            e.preventDefault();

            if (!currentResultId) {
                showNotification('No result selected', 'error');
                return;
            }

            let data = {};

            if (gameEvent === 'High Jump') {
                // High Jump specific data collection
                const attempts = {};
                const container = document.getElementById('highJumpAttemptsContainer');
                if (container) {
                    const attemptDivs = container.querySelectorAll('div[class*="border"]');

                    attemptDivs.forEach((div, index) => {
                        const heightInput = div.querySelector(`input[id*="Height"]`);
                        const resultSelect = div.querySelector(`select[id*="Attempt"]`);

                        if (heightInput && resultSelect && heightInput.value && resultSelect.value) {
                            attempts[index + 1] = {
                                height: parseFloat(heightInput.value),
                                value: resultSelect.value
                            };
                        }
                    });
                }

                data = {
                    high_jump_attempts: attempts,
                    record: document.getElementById('editRecord').value,
                    guide_sdms: document.getElementById('editGuideSdms').value
                };
            } else {
                // Other field events
                const attempts = {};
                for (let i = 1; i <= 6; i++) {
                    const attemptInput = document.getElementById(`editAttempt${i}`);
                    const windInput = document.getElementById(`editWind${i}`);

                    if (attemptInput && attemptInput.value.trim()) {
                        attempts[i] = {
                            value: attemptInput.value.trim(),
                            wind_velocity: windInput && windInput.value ? parseFloat(windInput.value) : null
                        };
                    }
                }

                data = {
                    attempts: attempts,
                    record: document.getElementById('editRecord').value,
                    weight: document.getElementById('editWeight').value,
                    guide_sdms: document.getElementById('editGuideSdms').value
                };
            }

            fetch(`/admin/results/${currentResultId}/update-attempts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    closeEditAttemptsModal();
                    showNotification('Attempts updated successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error updating attempts', 'error');
            });
        });
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initializeAthleteSearch();
    initializeGuideSearch();
    initializeFormHandlers();
    initializeDragAndDrop();
});

// Export global
window.selectAthlete = selectAthlete;
window.selectFromStartList = selectFromStartList;
window.selectGuide = selectGuide;
window.selectSpecialValue = selectSpecialValue;
window.togglePublish = togglePublish;
window.autoRankResults = autoRankResults;
window.selectFinalistsRound1 = selectFinalistsRound1;
window.recalculateRaza = recalculateRaza;
window.openGameEditModal = openGameEditModal;
window.closeGameEditModal = closeGameEditModal;
window.toggleAttempts = toggleAttempts;
window.deleteResult = deleteResult;
window.openGameEditModalFromGlobal = openGameEditModalFromGlobal;
window.editAttemptsFromGlobal = editAttemptsFromGlobal;
window.editAttempts = editAttempts;
window.closeEditAttemptsModal = closeEditAttemptsModal;
window.createHighJumpEditInterface = createHighJumpEditInterface;
window.showAddAttemptModal = showAddAttemptModal;
window.closeAddAttemptModal = closeAddAttemptModal;
window.addHighJumpAttempt = addHighJumpAttempt;
window.recalculateHighJump = recalculateHighJump;
window.toggleGameOfficial = toggleGameOfficial;