let searchTimeout;
let currentResultId = null;
const isFieldEvent = window.isFieldEvent || false;
const isTrackEvent = window.isTrackEvent || false;
const gameEvent = window.gameEvent || '';
const hasWpaPoints = window.hasWpaPoints || false;
const specialValues = window.specialValues || [
  'DNS',
  'DNF',
  'DQ',
  'NM',
  'X',
  'O',
  '-',
];
const gameId = window.gameId;
window.currentEventFilter = '';

// Retrieves CSRF token from hidden input field
function getCSRFToken() {
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  return csrfInput ? csrfInput.value : '';
}

// Displays temporary notification messages to user
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity ${
    type === 'success'
      ? 'bg-green-500 text-white'
      : type === 'error'
      ? 'bg-red-500 text-white'
      : 'bg-blue-500 text-white'
  }`;
  notification.textContent = message;
  document.body.appendChild(notification);
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Sets loading state for buttons with spinner animation
function setLoadingState(button, isLoading) {
  if (!button) return;
  if (isLoading) {
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    button.disabled = true;
  } else {
    button.innerHTML = button.dataset.originalText || '';
    button.disabled = false;
  }
}

// Initializes event filter dropdown with available events
function initializeEventFilter() {
  const eventFilterSelect = document.getElementById('eventFilter');
  if (!eventFilterSelect) return;

  fetch('/admin/api/events/list')
    .then((response) => response.json())
    .then((events) => {
      while (eventFilterSelect.children.length > 1) {
        eventFilterSelect.removeChild(eventFilterSelect.lastChild);
      }

      if (Array.isArray(events)) {
        events.forEach((event) => {
          const option = document.createElement('option');
          option.value = event;
          option.textContent = event;
          eventFilterSelect.appendChild(option);
        });
      }
    })
    .catch((error) => console.error('Error loading events:', error));

  eventFilterSelect.addEventListener('change', function () {
    const selectedEvent = this.value;
    window.currentEventFilter = selectedEvent;

    const athleteSearch = document.getElementById('athleteSearch');
    const selectedSdms = document.getElementById('selectedSdms');
    const selectedAthlete = document.getElementById('selectedAthlete');

    if (athleteSearch) athleteSearch.value = '';
    if (selectedSdms) selectedSdms.value = '';
    if (selectedAthlete) selectedAthlete.innerHTML = '';

    updateEventFilterStatus(selectedEvent);
  });
}

// Updates visual status indicator for active event filter
function updateEventFilterStatus(selectedEvent) {
  const existingStatus = document.getElementById('eventFilterStatus');
  if (existingStatus) existingStatus.remove();

  if (selectedEvent) {
    const filterStatus = document.createElement('div');
    filterStatus.id = 'eventFilterStatus';
    filterStatus.className =
      'text-sm bg-blue-50 text-blue-700 p-2 rounded border border-blue-200 mt-2';
    filterStatus.innerHTML = `
            <i class="fas fa-filter mr-1"></i>
            <strong>Event Filter Active:</strong> Only showing athletes registered for "${selectedEvent}"
            <button onclick="clearEventFilter()" class="ml-2 text-blue-600 hover:text-blue-800">
                <i class="fas fa-times"></i>
            </button>
        `;

    const athleteContainer =
      document.getElementById('selectedAthlete') ||
      document.querySelector('[data-game-classes]');
    if (athleteContainer && athleteContainer.parentNode) {
      athleteContainer.parentNode.insertBefore(filterStatus, athleteContainer);
    }
  }
}

// Clears active event filter
function clearEventFilter() {
  const eventFilterSelect = document.getElementById('eventFilter');
  if (eventFilterSelect) {
    eventFilterSelect.value = '';
    window.currentEventFilter = '';
    updateEventFilterStatus('');
  }
}

// Sets up athlete search input with debounced API calls
function initializeAthleteSearch() {
  const athleteSearch = document.getElementById('athleteSearch');
  const athleteResults = document.getElementById('athleteResults');
  if (!athleteSearch || !athleteResults) return;

  athleteSearch.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    if (query.length < 2) {
      athleteResults.classList.add('hidden');
      return;
    }

    searchTimeout = setTimeout(() => {
      let searchUrl = `/admin/api/athletes/search?q=${encodeURIComponent(query)}`;

      if (window.currentEventFilter) {
        searchUrl += `&event_filter=${encodeURIComponent(
          window.currentEventFilter
        )}`;
      }

      fetch(searchUrl)
        .then((response) => response.json())
        .then((athletes) => {
          displayAthleteSearchResults(athletes, query);
        })
        .catch((error) => {
          console.error('Search error:', error);
          athleteResults.innerHTML =
            '<div class="p-2 text-red-500">Search failed</div>';
          athleteResults.classList.remove('hidden');
        });
    }, 300);
  });
}

// Displays formatted search results for athletes
function displayAthleteSearchResults(athletes, query) {
  const athleteResults = document.getElementById('athleteResults');
  const selectedAthlete = document.getElementById('selectedAthlete');

  if (!athleteResults) return;

  const gameClasses = selectedAthlete && selectedAthlete.dataset && selectedAthlete.dataset.gameClasses
    ? selectedAthlete.dataset.gameClasses.split(',').map((c) => c.trim())
    : [];
  const gameGender = selectedAthlete && selectedAthlete.dataset
    ? selectedAthlete.dataset.gameGender || ''
    : '';

  athleteResults.innerHTML = '';

  if (!Array.isArray(athletes) || athletes.length === 0) {
    const noResultsMessage = window.currentEventFilter
      ? `No athletes found for "${query}" registered for "${window.currentEventFilter}"`
      : `No athletes found for "${query}"`;

    athleteResults.innerHTML = `
            <div class="p-3 text-gray-500">
                <div>${noResultsMessage}</div>
                <div class="text-xs mt-1">
                    ${
                      window.currentEventFilter
                        ? 'Try clearing the event filter or searching for different terms'
                        : 'Try searching by SDMS, name, NPC, or class (e.g., T47, F11)'
                    }
                </div>
                ${
                  window.currentEventFilter
                    ? `
                    <button onclick="clearEventFilter()" class="mt-2 text-blue-600 hover:text-blue-800 text-xs">
                        <i class="fas fa-times mr-1"></i>Clear event filter
                    </button>
                `
                    : ''
                }
            </div>
        `;
    athleteResults.classList.remove('hidden');
    return;
  }

  if (window.currentEventFilter) {
    const header = document.createElement('div');
    header.className =
      'p-2 bg-blue-50 text-sm font-medium text-blue-700 border-b';
    header.innerHTML = `
            <i class="fas fa-filter mr-2"></i>
            Athletes registered for "${window.currentEventFilter}" (${athletes.length} found)
        `;
    athleteResults.appendChild(header);
  }

  const isClassSearch =
    athletes.length > 10 &&
    athletes.every(
      (athlete) =>
        athlete.classes_list &&
        Array.isArray(athlete.classes_list) &&
        athlete.classes_list.some((c) =>
          c.toUpperCase().includes(query.toUpperCase())
        )
    );

  if (isClassSearch && !window.currentEventFilter) {
    const header = document.createElement('div');
    header.className =
      'p-2 bg-blue-50 text-sm font-medium text-blue-700 border-b';
    header.innerHTML = `<i class="fas fa-users mr-2"></i>Athletes in class "${query.toUpperCase()}" (${
      athletes.length
    } found)`;
    athleteResults.appendChild(header);

    athletes.forEach((athlete) => {
      athleteResults.appendChild(
        createAthleteResultElement(athlete, gameClasses, gameGender, true)
      );
    });
  } else {
    const exactMatches = [];
    const classMatches = [];
    const otherMatches = [];

    athletes.forEach((athlete) => {
      if (!athlete) return;

      const queryLower = query.toLowerCase();
      const sdms = athlete.sdms ? athlete.sdms.toString() : '';
      const name = athlete.name || (athlete.firstname && athlete.lastname ? `${athlete.firstname} ${athlete.lastname}` : '');
      const npc = athlete.npc || '';
      const athleteText = `${sdms} ${name} ${npc}`.toLowerCase();

      if (sdms === query) {
        exactMatches.push(athlete);
      } else if (athleteText.includes(queryLower)) {
        exactMatches.push(athlete);
      } else if (
        athlete.classes_list &&
        Array.isArray(athlete.classes_list) &&
        athlete.classes_list.some((c) => c && c.toLowerCase().includes(queryLower))
      ) {
        classMatches.push(athlete);
      } else {
        otherMatches.push(athlete);
      }
    });

    if (exactMatches.length > 0) {
      const header = document.createElement('div');
      header.className =
        'p-2 bg-gray-50 text-xs font-medium text-gray-600 border-b';
      header.textContent =
        exactMatches[0] && exactMatches[0].sdms && exactMatches[0].sdms.toString() === query
          ? 'Exact SDMS match:'
          : 'Direct matches:';
      athleteResults.appendChild(header);
      exactMatches.forEach((athlete) => {
        athleteResults.appendChild(
          createAthleteResultElement(athlete, gameClasses, gameGender)
        );
      });
    }

    if (classMatches.length > 0) {
      const header = document.createElement('div');
      header.className =
        'p-2 bg-blue-50 text-xs font-medium text-blue-700 border-b';
      header.textContent = 'Class matches:';
      athleteResults.appendChild(header);
      classMatches.forEach((athlete) => {
        athleteResults.appendChild(
          createAthleteResultElement(athlete, gameClasses, gameGender, true)
        );
      });
    }

    if (
      otherMatches.length > 0 &&
      exactMatches.length + classMatches.length < 15
    ) {
      const header = document.createElement('div');
      header.className =
        'p-2 bg-gray-50 text-xs font-medium text-gray-600 border-b';
      header.textContent = 'Other matches:';
      athleteResults.appendChild(header);
      otherMatches.slice(0, 5).forEach((athlete) => {
        athleteResults.appendChild(
          createAthleteResultElement(athlete, gameClasses, gameGender)
        );
      });
    }
  }

  athleteResults.classList.remove('hidden');
}

// Creates DOM element for individual athlete search result
function createAthleteResultElement(
  athlete,
  gameClasses = [],
  gameGender = '',
  isClassMatch = false
) {
  if (!athlete) return document.createElement('div');

  const div = document.createElement('div');
  div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';

  const athleteClasses = athlete.classes_list && Array.isArray(athlete.classes_list)
    ? athlete.classes_list
    : (athlete.class && typeof athlete.class === 'string'
      ? athlete.class.split(',').map((c) => c.trim())
      : []);

  const compatibleClasses = athleteClasses.filter((cls) =>
    gameClasses.includes(cls)
  );
  const classMatch = compatibleClasses.length > 0;
  const genderMatch = !gameGender || (athlete.gender && gameGender.includes(athlete.gender));

  let alertClass = '';
  let alertText = '';
  if (!classMatch && !genderMatch && gameClasses.length > 0) {
    alertClass = 'border-l-4 border-red-400 bg-red-50';
    alertText =
      '<div class="text-xs text-red-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Class & Gender mismatch</div>';
  } else if (!classMatch && gameClasses.length > 0) {
    alertClass = 'border-l-4 border-yellow-400 bg-yellow-50';
    alertText =
      '<div class="text-xs text-yellow-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Class mismatch</div>';
  } else if (!genderMatch && gameGender) {
    alertClass = 'border-l-4 border-yellow-400 bg-yellow-50';
    alertText =
      '<div class="text-xs text-yellow-600 mt-1"><i class="fas fa-exclamation-triangle"></i> Gender mismatch</div>';
  } else {
    alertClass = 'border-l-4 border-green-400 bg-green-50';
  }

  div.className += ' ' + alertClass;

  let classDisplay = '';
  if (athleteClasses.length > 0) {
    classDisplay = athleteClasses
      .map((cls) => {
        let highlight = '';
        if (isClassMatch) {
          highlight = 'bg-blue-100 text-blue-800 font-semibold';
        } else if (gameClasses.includes(cls)) {
          highlight = 'bg-green-100 text-green-800';
        } else {
          highlight = 'bg-gray-100 text-gray-600';
        }
        return `<span class="px-1 rounded text-xs ${highlight}">${cls}</span>`;
      })
      .join(' ');
  }

  let eventsDisplay = '';
  if (athlete.registered_events && typeof athlete.registered_events === 'string' && athlete.registered_events.trim()) {
    const events = athlete.registered_events.split(',').map(e => e.trim()).filter((e) => e);
    if (events.length > 0) {
      const displayEvents = events.slice(0, 3);
      const moreCount = events.length - 3;
      eventsDisplay = `
                <div class="text-xs text-purple-600 mt-1">
                    <i class="fas fa-clipboard-list mr-1"></i>
                    Events: ${displayEvents.join(', ')}${
        moreCount > 0 ? ` +${moreCount} more` : ''
      }
                </div>
            `;

      if (
        window.currentEventFilter &&
        events.includes(window.currentEventFilter)
      ) {
        eventsDisplay = eventsDisplay.replace(
          window.currentEventFilter,
          `<strong class="bg-purple-200 px-1 rounded">${window.currentEventFilter}</strong>`
        );
      }
    }
  } else if (window.currentEventFilter) {
    eventsDisplay =
      '<div class="text-xs text-gray-500 mt-1"><i class="fas fa-info-circle mr-1"></i>No registrations recorded</div>';
  }

  const athleteName = athlete.name ||
    (athlete.firstname && athlete.lastname ? `${athlete.firstname} ${athlete.lastname}` : 'Unknown');
  const sdms = athlete.sdms || 'N/A';
  const npc = athlete.npc || '';

  div.innerHTML = `
        <div class="flex justify-between items-center">
            <div>
                <strong>${sdms}</strong> - ${athleteName} (${npc})
            </div>
            <div class="text-right">
                <div class="flex flex-wrap gap-1 justify-end">${classDisplay}</div>
                <div class="text-xs text-gray-500 mt-1">${athlete.gender || ''}</div>
            </div>
        </div>
        ${eventsDisplay}
        ${alertText}
    `;

  div.onclick = () => {
    const athleteData = {
      sdms: athlete.sdms,
      name: athleteName,
      npc: athlete.npc || '',
      gender: athlete.gender || '',
      classes: athleteClasses,
      class: athlete.class || athleteClasses.join(','),
      registered_events: athlete.registered_events || '',
    };
    selectAthlete(athleteData);
  };

  return div;
}

// Sets up guide search functionality with debounced API calls
function initializeGuideSearch() {
  const guideSearch = document.getElementById('guideSearch');
  const guideResults = document.getElementById('guideResults');
  if (!guideSearch || !guideResults) return;

  guideSearch.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    const query = this.value.trim();
    if (query.length < 2) {
      guideResults.classList.add('hidden');
      return;
    }

    searchTimeout = setTimeout(() => {
      fetch(
        `/admin/athletes/search?q=${encodeURIComponent(query)}&guides=1`
      )
        .then((response) => response.json())
        .then((athletes) => {
          guideResults.innerHTML = '';
          if (!Array.isArray(athletes) || athletes.length === 0) {
            guideResults.innerHTML =
              '<div class="p-2 text-gray-500">No guides found</div>';
          } else {
            athletes.forEach((athlete) => {
              if (!athlete) return;
              const div = document.createElement('div');
              div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';
              const name = athlete.name ||
                (athlete.firstname && athlete.lastname ? `${athlete.firstname} ${athlete.lastname}` : 'Unknown');
              div.innerHTML = `<strong>${athlete.sdms || 'N/A'}</strong> - ${name} (${athlete.npc || ''})`;
              div.onclick = () => selectGuide(athlete);
              guideResults.appendChild(div);
            });
          }
          guideResults.classList.remove('hidden');
        })
        .catch((error) => {
          console.error('Guide search error:', error);
          guideResults.innerHTML = '<div class="p-2 text-red-500">Search failed</div>';
          guideResults.classList.remove('hidden');
        });
    }, 300);
  });
}

// Handles athlete selection and updates form fields
function selectAthlete(athlete) {
  if (!athlete) return;

  const selectedSdms = document.getElementById('selectedSdms');
  const athleteSearch = document.getElementById('athleteSearch');
  const athleteResults = document.getElementById('athleteResults');
  const selectedAthlete = document.getElementById('selectedAthlete');
  const selectedGuideSdms = document.getElementById('selectedGuideSdms');
  const selectedGuide = document.getElementById('selectedGuide');

  if (selectedSdms) selectedSdms.value = athlete.sdms || '';
  if (athleteSearch) athleteSearch.value = '';
  if (athleteResults) athleteResults.classList.add('hidden');
  if (selectedGuideSdms) selectedGuideSdms.value = '';
  if (selectedGuide) selectedGuide.innerHTML = '';

  if (selectedAthlete) {
    const gameClasses = selectedAthlete.dataset && selectedAthlete.dataset.gameClasses
      ? selectedAthlete.dataset.gameClasses.split(',').map((c) => c.trim())
      : [];
    const gameGender = selectedAthlete.dataset
      ? selectedAthlete.dataset.gameGender || ''
      : '';

    const athleteClasses = athlete.classes && Array.isArray(athlete.classes)
      ? athlete.classes
      : (athlete.class && typeof athlete.class === 'string'
        ? athlete.class.split(',').map((c) => c.trim())
        : []);

    const compatibleClasses = athleteClasses.filter((cls) =>
      gameClasses.includes(cls)
    );
    const classMatch = compatibleClasses.length > 0 || gameClasses.length === 0;
    const genderMatch = !gameGender || (athlete.gender && gameGender.includes(athlete.gender));

    let statusHtml = `Selected: <strong>${athlete.sdms || 'N/A'}</strong> - ${athlete.name || 'Unknown'}`;

    if (athleteClasses.length > 0) {
      const classesHtml = athleteClasses
        .map((cls) => {
          const isCompatible = gameClasses.includes(cls) || gameClasses.length === 0;
          return `<span class="px-1 rounded text-xs ${
            isCompatible
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }">${cls}</span>`;
        })
        .join(' ');
      statusHtml += `<div class="mt-1">Classes: ${classesHtml}</div>`;
    }

    if (athlete.registered_events && typeof athlete.registered_events === 'string' && athlete.registered_events.trim()) {
      const events = athlete.registered_events.split(',').map(e => e.trim()).filter((e) => e);
      if (events.length > 0) {
        const eventsHtml = events
          .map((event) => {
            const isCurrentEvent =
              window.currentEventFilter && event === window.currentEventFilter;
            return `<span class="px-1 rounded text-xs ${
              isCurrentEvent
                ? 'bg-purple-200 text-purple-800 font-semibold'
                : 'bg-blue-100 text-blue-800'
            }">${event}</span>`;
          })
          .join(' ');
        statusHtml += `<div class="mt-1">Registered Events: ${eventsHtml}</div>`;
      }
    }

    if (!classMatch && athleteClasses.length > 0 && gameClasses.length > 0) {
      statusHtml +=
        '<div class="text-yellow-600 text-xs mt-1"><i class="fas fa-exclamation-triangle"></i> Warning: No compatible class for this event</div>';
    }
    if (!genderMatch && gameGender) {
      statusHtml +=
        '<div class="text-yellow-600 text-xs mt-1"><i class="fas fa-exclamation-triangle"></i> Warning: Athlete gender does not match event gender</div>';
    }

    selectedAthlete.innerHTML = statusHtml;
  }
}

// Selects athlete from start list with optional guide
function selectFromStartList(
  sdms,
  name,
  gender,
  athleteClasses,
  guideSdms,
  registeredEvents
) {
  const athlete = {
    sdms: sdms,
    name: name,
    gender: gender,
    classes: athleteClasses && typeof athleteClasses === 'string'
      ? athleteClasses.split(',').map((c) => c.trim())
      : [],
    class: athleteClasses,
    registered_events: registeredEvents || '',
  };
  selectAthlete(athlete);

  if (guideSdms) {
    const selectedGuideSdms = document.getElementById('selectedGuideSdms');
    const selectedGuide = document.getElementById('selectedGuide');
    if (selectedGuideSdms) selectedGuideSdms.value = guideSdms;
    if (selectedGuide)
      selectedGuide.innerHTML = `Guide SDMS: <strong>${guideSdms}</strong>`;
  }
}

// Handles guide selection and updates form fields
function selectGuide(athlete) {
  if (!athlete) return;

  const sdmsInput =
    document.getElementById('selectedGuideSdms') ||
    document.getElementById('editGuideSdms');
  const searchInput =
    document.getElementById('guideSearch') ||
    document.getElementById('editGuideSearch');
  const resultsDiv =
    document.getElementById('guideResults') ||
    document.getElementById('editGuideResults');
  const displayDiv =
    document.getElementById('selectedGuide') ||
    document.getElementById('editSelectedGuide');

  const athleteName = athlete.name ||
    (athlete.firstname && athlete.lastname ? `${athlete.firstname} ${athlete.lastname}` : 'Unknown');

  if (sdmsInput) sdmsInput.value = athlete.sdms || '';
  if (searchInput) searchInput.value = '';
  if (resultsDiv) resultsDiv.classList.add('hidden');
  if (displayDiv)
    displayDiv.innerHTML = `Guide: <strong>${athlete.sdms || 'N/A'}</strong> - ${athleteName}`;
}

// Sets special performance values for results
function selectSpecialValue(value) {
  const performanceInput = document.getElementById('performanceValue');
  if (performanceInput && value) {
    performanceInput.value = value;
  }
}

// Toggles published status for a game
function togglePublish(gameIdParam, event) {
  const button = event.target.closest('button');
  setLoadingState(button, true);

  fetch(`/admin/games/${gameIdParam}/publish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        showNotification('Error: ' + data.error, 'error');
        setLoadingState(button, false);
      } else {
        location.reload();
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      showNotification('Error updating publish status', 'error');
      setLoadingState(button, false);
    });
}

// Automatically ranks all results in a game
function autoRankResults(gameIdParam, event) {
  if (confirm('Auto-rank all results? This will update ranks automatically.')) {
    const button = event.target.closest('button');
    setLoadingState(button, true);

    fetch(`/admin/games/${gameIdParam}/auto-rank`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification('Results auto-ranked successfully!', 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
          setLoadingState(button, false);
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error auto-ranking results', 'error');
        setLoadingState(button, false);
      });
  }
}

// Selects finalists for final round based on qualifying attempts
function selectFinalistsRound1(gameIdParam) {
  if (
    confirm(
      'Select finalists for final round based on qualifying attempts?'
    )
  ) {
    fetch(`/admin/games/${gameIdParam}/auto-rank-round1`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error selecting finalists', 'error');
      });
  }
}

// Recalculates WPA points for all results in a game
function recalculateRaza(gameIdParam) {
  if (confirm('Recalculate all WPA Points?')) {
    const button = event.target;
    setLoadingState(button, true);

    fetch(`/admin/games/${gameIdParam}/recalculate-raza`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(
            `WPA Points recalculated! Updated ${data.updated} results.`,
            'success'
          );
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
          setLoadingState(button, false);
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error recalculating WPA Points', 'error');
        setLoadingState(button, false);
      });
  }
}

// Opens game edit modal using global data
function openGameEditModalFromGlobal(gameId) {
  if (window.gameEditData) {
    openGameEditModal(gameId, window.gameEditData);
  } else {
    showNotification('Game data not found', 'error');
  }
}

// Opens modal for editing game details
function openGameEditModal(gameIdParam, gameData) {
  const modal = document.getElementById('gameEditModal');
  if (!modal) {
    showNotification('Game edit modal not found', 'error');
    return;
  }

  if (!gameData) {
    showNotification('Game data is missing', 'error');
    return;
  }

  const fields = {
    editGameId: gameIdParam,
    editEvent: gameData.event || '',
    editGenders: gameData.genders || '',
    editClasses: gameData.classes || '',
    editPhase: gameData.phase || '',
    editArea: gameData.area || '',
    editDay: gameData.day || '',
    editTime: gameData.time || '',
    editNbAthletes: gameData.nb_athletes || '',
    editStatus: gameData.status || '',
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

// Closes game edit modal
function closeGameEditModal() {
  const modal = document.getElementById('gameEditModal');
  if (modal) modal.classList.add('hidden');
}

// Opens attempts edit modal using global result data
function editAttemptsFromGlobal(resultId) {
  const resultData = window[`resultEditData_${resultId}`];
  if (resultData) {
    editAttempts(resultId, resultData);
  } else {
    showNotification('Result data not found', 'error');
  }
}

// Opens modal for editing result attempts
function editAttempts(resultId, resultData) {
  const modal = document.getElementById('editAttemptsModal');
  if (!modal) {
    showNotification('Edit attempts modal not found', 'error');
    return;
  }

  if (!resultData) {
    showNotification('Result data is missing', 'error');
    return;
  }

  currentResultId = resultId;
  const editResultIdField = document.getElementById('editResultId');
  if (editResultIdField) editResultIdField.value = resultId;

  if (resultData.attempts && Array.isArray(resultData.attempts)) {
    if (gameEvent === 'High Jump') {
      createHighJumpEditInterface(resultData.attempts);
    } else {
      resultData.attempts.forEach((attempt, index) => {
        if (!attempt) return;

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

// Creates interface for editing high jump attempts
function createHighJumpEditInterface(attempts) {
  const container = document.getElementById('highJumpAttemptsContainer');
  if (!container) {
    console.warn('High Jump attempts container not found');
    return;
  }

  if (!Array.isArray(attempts)) {
    console.warn('Attempts is not an array');
    return;
  }

  container.innerHTML = '';

  attempts.forEach((attempt, index) => {
    if (!attempt) return;

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
                    <option value="O" ${
                      attempt.value === 'O' ? 'selected' : ''
                    }>O (Success)</option>
                    <option value="X" ${
                      attempt.value === 'X' ? 'selected' : ''
                    }>X (Failure)</option>
                    <option value="-" ${
                      attempt.value === '-' ? 'selected' : ''
                    }>- (Pass)</option>
                    <option value="XO" ${
                      attempt.value === 'XO' ? 'selected' : ''
                    }>XO</option>
                    <option value="XXO" ${
                      attempt.value === 'XXO' ? 'selected' : ''
                    }>XXO</option>
                    <option value="XXX" ${
                      attempt.value === 'XXX' ? 'selected' : ''
                    }>XXX (Elimination)</option>
                </select>
            </div>
        `;
    container.appendChild(attemptDiv);
  });

  const newAttemptDiv = document.createElement('div');
  newAttemptDiv.className =
    'border-2 border-dashed border-purple-300 rounded p-3 bg-purple-50';
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

// Closes attempts edit modal
function closeEditAttemptsModal() {
  const modal = document.getElementById('editAttemptsModal');
  if (modal) {
    modal.classList.add('hidden');
    currentResultId = null;
  }
}

// Toggles visibility of attempt details
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

// Deletes a result after confirmation
function deleteResult(resultId) {
  if (confirm('Delete this result?')) {
    const formData = new FormData();
    formData.append('csrf_token', getCSRFToken());

    fetch(`/admin/results/${resultId}/delete`, {
      method: 'POST',
      body: formData,
    })
      .then((response) => {
        if (response.ok) {
          const row = document.querySelector(`tr[data-result-id="${resultId}"]`);
          if (row) row.remove();
          showNotification('Result deleted successfully', 'success');
        } else {
          showNotification('Error deleting result', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error deleting result', 'error');
      });
  }
}

// Shows modal for adding new attempt
function showAddAttemptModal(resultId) {
  currentResultId = resultId;
  const modal = document.getElementById('addAttemptModal');
  if (modal) {
    modal.classList.remove('hidden');
  }
}

// Closes add attempt modal
function closeAddAttemptModal() {
  const modal = document.getElementById('addAttemptModal');
  if (modal) {
    modal.classList.add('hidden');
    currentResultId = null;
  }
}

// Adds new high jump attempt to result
function addHighJumpAttempt() {
  if (!currentResultId) {
    showNotification('No result selected', 'error');
    return;
  }

  const heightInput = document.getElementById('attemptHeight');
  const resultInput = document.getElementById('attemptResult');

  const height = heightInput ? heightInput.value : '';
  const result = resultInput ? resultInput.value : '';

  if (!height || !result) {
    showNotification('Height and result are required', 'error');
    return;
  }

  const data = {
    height: parseFloat(height),
    result: result,
  };

  fetch(`/admin/results/${currentResultId}/add-attempt`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        closeAddAttemptModal();
        showNotification('Attempt added successfully!', 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      showNotification('Error adding attempt', 'error');
    });
}

// Initializes drag and drop functionality for result rankings
function initializeDragAndDrop() {
  const tbody = document.getElementById('sortableResults');
  if (!tbody || typeof Sortable === 'undefined') return;

  new Sortable(tbody, {
    animation: 150,
    ghostClass: 'sortable-ghost',
    onEnd: function (evt) {
      updateManualRanking();
    },
  });
}

// Updates manual ranking after drag and drop
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
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify({ rankings: rankings }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification('Rankings updated', 'success');
      } else {
        showNotification('Error updating rankings', 'error');
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      showNotification('Error updating rankings', 'error');
    });
}

// Recalculates high jump ranking with proper tie-breaking rules
function recalculateHighJump(gameIdParam) {
  if (
    confirm(
      'Recalculate High Jump ranking with proper tie-breaking rules?'
    )
  ) {
    const button = event.target;
    setLoadingState(button, true);

    fetch(`/admin/games/${gameIdParam}/recalculate-high-jump`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(
            'High Jump ranking recalculated successfully!',
            'success'
          );
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
          setLoadingState(button, false);
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error recalculating High Jump ranking', 'error');
        setLoadingState(button, false);
      });
  }
}

// Toggles official status for entire game and all its results
function toggleGameOfficial(gameId) {
  const confirmMessage =
    'Are you sure you want to change the official status of this entire game and ALL its results?';
  if (!confirm(confirmMessage)) {
    return;
  }

  const button = event.target.closest('button');
  setLoadingState(button, true);

  fetch(`/admin/games/${gameId}/toggle-official`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification(data.message, 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
        setLoadingState(button, false);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      showNotification('Error changing official status', 'error');
      setLoadingState(button, false);
    });
}

// Initializes form submission handlers
function initializeFormHandlers() {
  const gameEditForm = document.getElementById('gameEditForm');
  if (gameEditForm) {
    gameEditForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      const gameIdField = document.getElementById('editGameId');
      const gameIdValue = gameIdField ? gameIdField.value : '';

      if (!gameIdValue) {
        showNotification('Game ID not found', 'error');
        return;
      }

      fetch(`/admin/games/${gameIdValue}/edit`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: formData,
      })
        .then((response) => {
          if (response.ok) {
            closeGameEditModal();
            showNotification('Game updated successfully!', 'success');
            setTimeout(() => location.reload(), 1000);
          } else {
            showNotification('Error updating game', 'error');
          }
        })
        .catch((error) => {
          console.error('Error:', error);
          showNotification('Error updating game', 'error');
        });
    });
  }

  const editAttemptsForm = document.getElementById('editAttemptsForm');
  if (editAttemptsForm) {
    editAttemptsForm.addEventListener('submit', function (e) {
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
            if (
              heightInput &&
              resultSelect &&
              heightInput.value &&
              resultSelect.value
            ) {
              attempts[index + 1] = {
                height: parseFloat(heightInput.value),
                value: resultSelect.value,
              };
            }
          });
        }

        const recordField = document.getElementById('editRecord');
        const guideField = document.getElementById('editGuideSdms');

        data = {
          high_jump_attempts: attempts,
          record: recordField ? recordField.value : '',
          guide_sdms: guideField ? guideField.value : '',
        };
      } else {
        const attempts = {};
        for (let i = 1; i <= 6; i++) {
          const attemptInput = document.getElementById(`editAttempt${i}`);
          const windInput = document.getElementById(`editWind${i}`);
          if (attemptInput && attemptInput.value.trim()) {
            attempts[i] = {
              value: attemptInput.value.trim(),
              wind_velocity:
                windInput && windInput.value
                  ? parseFloat(windInput.value)
                  : null,
            };
          }
        }

        const recordField = document.getElementById('editRecord');
        const weightField = document.getElementById('editWeight');
        const guideField = document.getElementById('editGuideSdms');

        data = {
          attempts: attempts,
          record: recordField ? recordField.value : '',
          weight: weightField ? weightField.value : '',
          guide_sdms: guideField ? guideField.value : '',
        };
      }

      fetch(`/admin/results/${currentResultId}/update-attempts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(data),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            closeEditAttemptsModal();
            showNotification('Attempts updated successfully!', 'success');
            setTimeout(() => location.reload(), 1000);
          } else {
            showNotification(
              'Error: ' + (data.error || 'Unknown error'),
              'error'
            );
          }
        })
        .catch((error) => {
          console.error('Error:', error);
          showNotification('Error updating attempts', 'error');
        });
    });
  }
}

// Publishes auto-generated start list PDF
function publishAutoStartlistPdf(gameId) {
  if (confirm('Generate and publish start list PDF automatically?')) {
    fetch(`/admin/games/${gameId}/publish-auto-pdfs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ type: 'startlist' }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(data.error || 'Error publishing PDF', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error publishing PDF', 'error');
      });
  }
}

// Publishes auto-generated results PDF
function publishAutoResultsPdf(gameId) {
  if (confirm('Generate and publish results PDF automatically?')) {
    fetch(`/admin/games/${gameId}/publish-auto-pdfs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ type: 'results' }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(data.error || 'Error publishing PDF', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error publishing PDF', 'error');
      });
  }
}

// Publishes both start list and results PDFs automatically
function publishAutoPdfs(gameId) {
  if (
    confirm(
      'Generate and publish both start list and results PDFs automatically?'
    )
  ) {
    fetch(`/admin/games/${gameId}/publish-auto-pdfs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(data.error || 'Error publishing PDFs', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error publishing PDFs', 'error');
      });
  }
}

// Bulk generates PDFs for multiple games
function bulkGeneratePdfs(type) {
  const typeText = type === 'startlists' ? 'start lists' : 'results';
  if (confirm(`Generate all missing ${typeText} PDFs? This may take a while.`)) {
    showNotification(`Generating ${typeText} PDFs...`, 'info');

    fetch('/admin/bulk-generate-pdfs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ type: type }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          setTimeout(() => location.reload(), 2000);
        } else {
          showNotification(
            data.error || `Error generating ${typeText}`,
            'error'
          );
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification(`Error generating ${typeText}`, 'error');
      });
  }
}

// Adds athlete to start list with optional guide
function addAthleteToStartlist(gameId, athleteSdms, guideSdms = null) {
  if (confirm('Add this athlete to the start list?')) {
    fetch(`/admin/games/${gameId}/add-to-startlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        athlete_sdms: athleteSdms,
        guide_sdms: guideSdms,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(data.message, 'success');
          const addButton = document.querySelector(
            `[data-add-startlist="${athleteSdms}"]`
          );
          if (addButton) {
            addButton.remove();
          }
        } else {
          showNotification(data.error || 'Error adding to start list', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error adding to start list', 'error');
      });
  }
}

// Opens start list PDF in new tab
function viewStartlistPdf(gameId) {
  window.open(`/admin/games/${gameId}/view-startlist-pdf`, '_blank');
}

// Opens results PDF in new tab
function viewResultsPdf(gameId) {
  window.open(`/admin/games/${gameId}/view-results-pdf`, '_blank');
}

// Deletes start list PDF after confirmation
function deleteStartlistPdf(gameId) {
  if (confirm('Delete the start list PDF? This action cannot be undone.')) {
    fetch(`/admin/games/${gameId}/delete-startlist-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification('Start list PDF deleted successfully', 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(data.error || 'Error deleting PDF', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error deleting PDF', 'error');
      });
  }
}

// Deletes results PDF after confirmation
function deleteResultsPdf(gameId) {
  if (confirm('Delete the results PDF? This action cannot be undone.')) {
    fetch(`/admin/games/${gameId}/delete-results-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification('Results PDF deleted successfully', 'success');
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(data.error || 'Error deleting PDF', 'error');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        showNotification('Error deleting PDF', 'error');
      });
  }
}

// Closes dropdowns when clicking outside
document.addEventListener('click', function (e) {
  const athleteSearch = document.getElementById('athleteSearch');
  const athleteResults = document.getElementById('athleteResults');
  const guideSearch = document.getElementById('guideSearch');
  const guideResults = document.getElementById('guideResults');

  if (
    athleteSearch &&
    athleteResults &&
    !athleteSearch.contains(e.target) &&
    !athleteResults.contains(e.target)
  ) {
    athleteResults.classList.add('hidden');
  }
  if (
    guideSearch &&
    guideResults &&
    !guideSearch.contains(e.target) &&
    !guideResults.contains(e.target)
  ) {
    guideResults.classList.add('hidden');
  }
});

// Main initialization when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
  initializeAthleteSearch();
  initializeGuideSearch();
  initializeFormHandlers();
  initializeDragAndDrop();
  initializeEventFilter();
});

// Export functions to global scope
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
window.publishAutoStartlistPdf = publishAutoStartlistPdf;
window.publishAutoResultsPdf = publishAutoResultsPdf;
window.publishAutoPdfs = publishAutoPdfs;
window.bulkGeneratePdfs = bulkGeneratePdfs;
window.addAthleteToStartlist = addAthleteToStartlist;
window.viewStartlistPdf = viewStartlistPdf;
window.viewResultsPdf = viewResultsPdf;
window.deleteStartlistPdf = deleteStartlistPdf;
window.deleteResultsPdf = deleteResultsPdf;