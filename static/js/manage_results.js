let searchTimeout;
let currentResultId = null;
const isFieldEvent = window.isFieldEvent || false;
const isTrackEvent = window.isTrackEvent || false;
const gameEvent = window.gameEvent || '';
const hasWpaPoints = window.hasWpaPoints || false;
const specialValues = window.specialValues || ['DNS', 'DNF', 'DQ', 'NM', 'X', 'O', '-'];
const gameId = window.gameId;

// Global event filter state
window.currentEventFilter = '';

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

function initializeEventFilter() {
    const eventFilterSelect = document.getElementById('eventFilter');
    if (!eventFilterSelect) return;

    // Load events for filter
    fetch('/admin/api/events/list')
        .then(response => response.json())
        .then(events => {
            // Clear existing options except the first one
            while (eventFilterSelect.children.length > 1) {
                eventFilterSelect.removeChild(eventFilterSelect.lastChild);
            }

            events.forEach(event => {
                const option = document.createElement('option');
                option.value = event;
                option.textContent = event;
                eventFilterSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading events:', error));

    eventFilterSelect.addEventListener('change', function() {
        const selectedEvent = this.value;
        window.currentEventFilter = selectedEvent;

        // Clear current athlete selection
        const athleteSearch = document.getElementById('athleteSearch');
        const selectedSdms = document.getElementById('selectedSdms');
        const selectedAthlete = document.getElementById('selectedAthlete');

        if (athleteSearch) athleteSearch.value = '';
        if (selectedSdms) selectedSdms.value = '';
        if (selectedAthlete) selectedAthlete.innerHTML = '';

        // Show/hide filter status
        updateEventFilterStatus(selectedEvent);
    });
}

function updateEventFilterStatus(selectedEvent) {
    const existingStatus = document.getElementById('eventFilterStatus');
    if (existingStatus) existingStatus.remove();

    if (selectedEvent) {
        const filterStatus = document.createElement('div');
        filterStatus.id = 'eventFilterStatus';
        filterStatus.className = 'text-sm bg-blue-50 text-blue-700 p-2 rounded border border-blue-200 mt-2';
        filterStatus.innerHTML = `
            <i class="fas fa-filter mr-1"></i>
            <strong>Event Filter Active:</strong> Only showing athletes registered for "${selectedEvent}"
            <button onclick="clearEventFilter()" class="ml-2 text-blue-600 hover:text-blue-800">
                <i class="fas fa-times"></i>
            </button>
        `;

        const athleteContainer = document.getElementById('selectedAthlete') || document.querySelector('[data-game-classes]');
        if (athleteContainer && athleteContainer.parentNode) {
            athleteContainer.parentNode.insertBefore(filterStatus, athleteContainer);
        }
    }
}

function clearEventFilter() {
    const eventFilterSelect = document.getElementById('eventFilter');
    if (eventFilterSelect) {
        eventFilterSelect.value = '';
        window.currentEventFilter = '';
        updateEventFilterStatus('');
    }
}

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
            let searchUrl = `/admin/api/athletes/search?q=${encodeURIComponent(query)}`;

            // Add event filter if present
            if (window.currentEventFilter) {
                searchUrl += `&event_filter=${encodeURIComponent(window.currentEventFilter)}`;
            }

            fetch(searchUrl)
                .then(response => response.json())
                .then(athletes => {
                    displayAthleteSearchResults(athletes, query);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    athleteResults.innerHTML = '<div class="p-2 text-red-500">Search failed</div>';
                    athleteResults.classList.remove('hidden');
                });
        }, 300);
    });
}

function displayAthleteSearchResults(athletes, query) {
    const athleteResults = document.getElementById('athleteResults');
    const selectedAthlete = document.getElementById('selectedAthlete');
    const gameClasses = selectedAthlete ? selectedAthlete.dataset.gameClasses.split(',').map(c => c.trim()) : [];
    const gameGender = selectedAthlete ? selectedAthlete.dataset.gameGender : '';

    athleteResults.innerHTML = '';

    if (athletes.length === 0) {
        const noResultsMessage = window.currentEventFilter
            ? `No athletes found for "${query}" registered for "${window.currentEventFilter}"`
            : `No athletes found for "${query}"`;

        athleteResults.innerHTML = `
            <div class="p-3 text-gray-500">
                <div>${noResultsMessage}</div>
                <div class="text-xs mt-1">
                    ${window.currentEventFilter 
                        ? 'Try clearing the event filter or searching for different terms'
                        : 'Try searching by SDMS, name, NPC, or class (e.g., T47, F11)'
                    }
                </div>
                ${window.currentEventFilter ? `
                    <button onclick="clearEventFilter()" class="mt-2 text-blue-600 hover:text-blue-800 text-xs">
                        <i class="fas fa-times mr-1"></i>Clear event filter
                    </button>
                ` : ''}
            </div>
        `;
        athleteResults.classList.remove('hidden');
        return;
    }

    // Add header if event filter is active
    if (window.currentEventFilter) {
        const header = document.createElement('div');
        header.className = 'p-2 bg-blue-50 text-sm font-medium text-blue-700 border-b';
        header.innerHTML = `
            <i class="fas fa-filter mr-2"></i>
            Athletes registered for "${window.currentEventFilter}" (${athletes.length} found)
        `;
        athleteResults.appendChild(header);
    }

    const isClassSearch = athletes.length > 10 && athletes.every(athlete =>
        athlete.classes_list && athlete.classes_list.some(c =>
            c.toUpperCase().includes(query.toUpperCase())
        )
    );

    if (isClassSearch && !window.currentEventFilter) {
        const header = document.createElement('div');
        header.className = 'p-2 bg-blue-50 text-sm font-medium text-blue-700 border-b';
        header.innerHTML = `<i class="fas fa-users mr-2"></i>Athletes in class "${query.toUpperCase()}" (${athletes.length} found)`;
        athleteResults.appendChild(header);

        athletes.forEach(athlete => {
            athleteResults.appendChild(createAthleteResultElement(athlete, gameClasses, gameGender, true));
        });
    } else {
        const exactMatches = [];
        const classMatches = [];
        const otherMatches = [];

        athletes.forEach(athlete => {
            const queryLower = query.toLowerCase();
            const athleteText = `${athlete.sdms} ${athlete.name || (athlete.firstname + ' ' + athlete.lastname)} ${athlete.npc}`.toLowerCase();

            if (athlete.sdms.toString() === query) {
                exactMatches.push(athlete);
            } else if (athleteText.includes(queryLower)) {
                exactMatches.push(athlete);
            } else if (athlete.classes_list && athlete.classes_list.some(c =>
                c.toLowerCase().includes(queryLower)
            )) {
                classMatches.push(athlete);
            } else {
                otherMatches.push(athlete);
            }
        });

        if (exactMatches.length > 0) {
            const header = document.createElement('div');
            header.className = 'p-2 bg-gray-50 text-xs font-medium text-gray-600 border-b';
            header.textContent = exactMatches[0].sdms.toString() === query ? 'Exact SDMS match:' : 'Direct matches:';
            athleteResults.appendChild(header);
            exactMatches.forEach(athlete => {
                athleteResults.appendChild(createAthleteResultElement(athlete, gameClasses, gameGender));
            });
        }

        if (classMatches.length > 0) {
            const header = document.createElement('div');
            header.className = 'p-2 bg-blue-50 text-xs font-medium text-blue-700 border-b';
            header.textContent = 'Class matches:';
            athleteResults.appendChild(header);
            classMatches.forEach(athlete => {
                athleteResults.appendChild(createAthleteResultElement(athlete, gameClasses, gameGender, true));
            });
        }

        if (otherMatches.length > 0 && (exactMatches.length + classMatches.length) < 15) {
            const header = document.createElement('div');
            header.className = 'p-2 bg-gray-50 text-xs font-medium text-gray-600 border-b';
            header.textContent = 'Other matches:';
            athleteResults.appendChild(header);
            otherMatches.slice(0, 5).forEach(athlete => {
                athleteResults.appendChild(createAthleteResultElement(athlete, gameClasses, gameGender));
            });
        }
    }

    athleteResults.classList.remove('hidden');
}

function createAthleteResultElement(athlete, gameClasses, gameGender, isClassMatch = false) {
    const div = document.createElement('div');
    div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';

    const athleteClasses = athlete.classes_list || (athlete.class ? athlete.class.split(',').map(c => c.trim()) : []);
    const compatibleClasses = athleteClasses.filter(cls => gameClasses.includes(cls));
    const classMatch = compatibleClasses.length > 0;
    const genderMatch = gameGender.includes(athlete.gender);

    let alertClass = '';
    let alertText = '';
    if (!classMatch && !genderMatch && gameClasses.length > 0) {
        alertClass = 'border-l-4 border-red-400 bg-red-50';
        alertText = '<div class="text-xs text-red-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Class & Gender mismatch</div>';
    } else if (!classMatch && gameClasses.length > 0) {
        alertClass = 'border-l-4 border-yellow-400 bg-yellow-50';
        alertText = '<div class="text-xs text-yellow-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Class mismatch</div>';
    } else if (!genderMatch && gameGender) {
        alertClass = 'border-l-4 border-yellow-400 bg-yellow-50';
        alertText = '<div class="text-xs text-yellow-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Gender mismatch</div>';
    } else {
        alertClass = 'border-l-4 border-green-400 bg-green-50';
    }

    div.className += ' ' + alertClass;

    let classDisplay = '';
    if (athleteClasses.length > 0) {
        classDisplay = athleteClasses.map(cls => {
            let highlight = '';
            if (isClassMatch) {
                highlight = 'bg-blue-100 text-blue-800 font-semibold';
            } else if (gameClasses.includes(cls)) {
                highlight = 'bg-green-100 text-green-800';
            } else {
                highlight = 'bg-gray-100 text-gray-600';
            }
            return `<span class="px-1 rounded text-xs ${highlight}">${cls}</span>`;
        }).join(' ');
    }

    let eventsDisplay = '';
    if (athlete.registered_events && athlete.registered_events.trim()) {
        const events = athlete.registered_events.split(', ').filter(e => e.trim());
        if (events.length > 0) {
            const displayEvents = events.slice(0, 3);
            const moreCount = events.length - 3;
            eventsDisplay = `
                <div class="text-xs text-purple-600 mt-1">
                    <i class="fas fa-clipboard-list mr-1"></i>
                    Events: ${displayEvents.join(', ')}${moreCount > 0 ? ` +${moreCount} more` : ''}
                </div>
            `;

            // Highlight current event filter
            if (window.currentEventFilter && events.includes(window.currentEventFilter)) {
                eventsDisplay = eventsDisplay.replace(
                    window.currentEventFilter,
                    `<strong class="bg-purple-200 px-1 rounded">${window.currentEventFilter}</strong>`
                );
            }
        }
    } else if (window.currentEventFilter) {
        eventsDisplay = '<div class="text-xs text-gray-500 mt-1"><i class="fas fa-info-circle mr-1"></i>No registrations recorded</div>';
    }

    const athleteName = athlete.name || `${athlete.firstname} ${athlete.lastname}`;
    div.innerHTML = `
        <div class="flex justify-between items-center">
            <div>
                <strong>${athlete.sdms}</strong> - ${athleteName} (${athlete.npc})
            </div>
            <div class="text-right">
                <div class="flex flex-wrap gap-1 justify-end">${classDisplay}</div>
                <div class="text-xs text-gray-500 mt-1">${athlete.gender}</div>
            </div>
        </div>
        ${eventsDisplay}
        ${alertText}
    `;

    div.onclick = () => {
        const athleteData = {
            sdms: athlete.sdms,
            name: athleteName,
            npc: athlete.npc,
            gender: athlete.gender,
            classes: athleteClasses,
            class: athlete.class || athleteClasses.join(','),
            registered_events: athlete.registered_events
        };
        selectAthlete(athleteData);
    };

    return div;
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
                        guideResults.innerHTML = '<div class="p-2 text-gray-500">No guides found</div>';
                    } else {
                        athletes.forEach(athlete => {
                            const div = document.createElement('div');
                            div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';
                            div.innerHTML = `<strong>${athlete.sdms}</strong> - ${athlete.name || athlete.firstname + ' ' + athlete.lastname} (${athlete.npc})`;
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
    if (selectedGuideSdms) selectedGuideSdms.value = '';
    if (selectedGuide) selectedGuide.innerHTML = '';

    if (selectedAthlete) {
        const gameClasses = selectedAthlete.dataset.gameClasses ? selectedAthlete.dataset.gameClasses.split(',').map(c => c.trim()) : [];
        const gameGender = selectedAthlete.dataset.gameGender;

        const athleteClasses = athlete.classes || (athlete.class ? athlete.class.split(',').map(c => c.trim()) : []);
        const compatibleClasses = athleteClasses.filter(cls => gameClasses.includes(cls));
        const classMatch = compatibleClasses.length > 0 || gameClasses.length === 0;
        const genderMatch = !gameGender || gameGender.includes(athlete.gender);

        let statusHtml = `Selected: <strong>${athlete.sdms}</strong> - ${athlete.name}`;

        if (athleteClasses.length > 0) {
            const classesHtml = athleteClasses.map(cls => {
                const isCompatible = gameClasses.includes(cls) || gameClasses.length === 0;
                return `<span class="px-1 rounded text-xs ${isCompatible ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${cls}</span>`;
            }).join(' ');
            statusHtml += `<div class="mt-1">Classes: ${classesHtml}</div>`;
        }

        if (athlete.registered_events && athlete.registered_events.trim()) {
            const events = athlete.registered_events.split(', ').filter(e => e.trim());
            if (events.length > 0) {
                const eventsHtml = events.map(event => {
                    const isCurrentEvent = window.currentEventFilter && event === window.currentEventFilter;
                    return `<span class="px-1 rounded text-xs ${isCurrentEvent ? 'bg-purple-200 text-purple-800 font-semibold' : 'bg-blue-100 text-blue-800'}">${event}</span>`;
                }).join(' ');
                statusHtml += `<div class="mt-1">Registered Events: ${eventsHtml}</div>`;
            }
        }

        if (!classMatch && athleteClasses.length > 0 && gameClasses.length > 0) {
            statusHtml += '<div class="text-yellow-600 text-xs mt-1"><i class="fas fa-exclamation-triangle"></i> Warning: No compatible class for this event</div>';
        }
        if (!genderMatch && gameGender) {
            statusHtml += '<div class="text-yellow-600 text-xs mt-1"><i class="fas fa-exclamation-triangle"></i> Warning: Athlete gender does not match event gender</div>';
        }

        selectedAthlete.innerHTML = statusHtml;
    }
}

function selectFromStartList(sdms, name, gender, athleteClasses, guideSdms, registeredEvents) {
    const athlete = {
        sdms: sdms,
        name: name,
        gender: gender,
        classes: athleteClasses ? athleteClasses.split(',').map(c => c.trim()) : [],
        class: athleteClasses,
        registered_events: registeredEvents || ''
    };
    selectAthlete(athlete);

    if (guideSdms) {
        const selectedGuideSdms = document.getElementById('selectedGuideSdms');
        const selectedGuide = document.getElementById('selectedGuide');
        if (selectedGuideSdms) selectedGuideSdms.value = guideSdms;
        if (selectedGuide) selectedGuide.innerHTML = `Guide SDMS: <strong>${guideSdms}</strong>`;
    }
}

function selectGuide(athlete) {
    const sdmsInput = document.getElementById('selectedGuideSdms') || document.getElementById('editGuideSdms');
    const searchInput = document.getElementById('guideSearch') || document.getElementById('editGuideSearch');
    const resultsDiv = document.getElementById('guideResults') || document.getElementById('editGuideResults');
    const displayDiv = document.getElementById('selectedGuide') || document.getElementById('editSelectedGuide');

    const athleteName = athlete.name || `${athlete.firstname} ${athlete.lastname}`;

    if (sdmsInput) sdmsInput.value = athlete.sdms;
    if (searchInput) searchInput.value = '';
    if (resultsDiv) resultsDiv.classList.add('hidden');
    if (displayDiv) displayDiv.innerHTML = `Guide: <strong>${athlete.sdms}</strong> - ${athleteName}`;
}

function selectSpecialValue(value) {
    const performanceInput = document.getElementById('performanceValue');
    if (performanceInput && value) {
        performanceInput.value = value;
    }
}

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
    if (confirm('Recalculate all WPA Points?')) {
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
                showNotification(`WPA Points recalculated! Updated ${data.updated} results.`, 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
                setLoadingState(button, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error recalculating WPA Points', 'error');
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

function openGameEditModal(gameIdParam, gameData) {
    const modal = document.getElementById('gameEditModal');
    if (!modal) {
        showNotification('Game edit modal not found', 'error');
        return;
    }

    const fields = {
        'editGameId': gameIdParam,
        'editEvent': gameData.event,
        'editGenders': gameData.genders,
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

    if (resultData.attempts) {
        if (gameEvent === 'High Jump') {
            createHighJumpEditInterface(resultData.attempts);
        } else {
            resultData.attempts.forEach((attempt, index) => {
                const attemptInput = document.getElementById(`editAttempt${index + 1}`);
                if (attemptInput && attempt.value) {
                    attemptInput.value = attempt.value;
                }

                const windInput = document.getElementById(`editWind${index + 1}`);
                if (windInput && attempt.wind_velocity) {
                    windInput.value = attempt.wind_velocity;
                }
            });
        }
    }

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

    container.innerHTML = '';

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

function initializeDragAndDrop() {
    const tbody = document.getElementById('sortableResults');
    if (!tbody || typeof Sortable === 'undefined') return;

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

// Event listeners for closing dropdowns when clicking outside
document.addEventListener('click', function(e) {
    const athleteSearch = document.getElementById('athleteSearch');
    const athleteResults = document.getElementById('athleteResults');
    const guideSearch = document.getElementById('guideSearch');
    const guideResults = document.getElementById('guideResults');

    if (athleteSearch && athleteResults && !athleteSearch.contains(e.target) && !athleteResults.contains(e.target)) {
        athleteResults.classList.add('hidden');
    }
    if (guideSearch && guideResults && !guideSearch.contains(e.target) && !guideResults.contains(e.target)) {
        guideResults.classList.add('hidden');
    }
});

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeAthleteSearch();
    initializeGuideSearch();
    initializeFormHandlers();
    initializeDragAndDrop();
    initializeEventFilter();
});

// Global function exports
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
window.displayAthleteSearchResults = displayAthleteSearchResults;
window.createAthleteResultElement = createAthleteResultElement;
window.clearEventFilter = clearEventFilter;
window.initializeEventFilter = initializeEventFilter;