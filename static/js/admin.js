document.addEventListener('DOMContentLoaded', function() {
    initAthleteSearch();
    initResultValidation();
    initStatusUpdates();
    initAttemptsHandling();
});
function initAthleteSearch() {
    const searchInputs = document.querySelectorAll('.athlete-search');
    searchInputs.forEach(input => {
        let searchTimeout;
        const resultsDiv = input.nextElementSibling;
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            if (query.length < 2) {
                resultsDiv.classList.add('hidden');
                return;
            }
            searchTimeout = setTimeout(() => {
                searchAthletes(query, resultsDiv);
            }, 300);
        });
    });
}
async function searchAthletes(query, resultsDiv) {
    try {
        const response = await fetch(`/admin/athletes/search?q=${encodeURIComponent(query)}`);
        const athletes = await response.json();
        resultsDiv.innerHTML = '';
        if (athletes.length === 0) {
            resultsDiv.innerHTML = '<div class="p-2 text-gray-500">No athletes found</div>';
        } else {
            athletes.forEach(athlete => {
                const div = document.createElement('div');
                div.className = 'p-2 hover:bg-gray-100 cursor-pointer border-b';
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <div>
                            <strong>${athlete.sdms}</strong> - ${athlete.name}
                            <span class="text-sm text-gray-600">(${athlete.npc})</span>
                        </div>
                        <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${athlete.class}</span>
                    </div>
                `;
                div.addEventListener('click', () => selectAthlete(athlete, resultsDiv));
                resultsDiv.appendChild(div);
            });
        }
        resultsDiv.classList.remove('hidden');
    } catch (error) {
        console.error('Error searching athletes:', error);
    }
}
function selectAthlete(athlete, resultsDiv) {
    const input = resultsDiv.previousElementSibling;
    const hiddenInput = document.getElementById('selectedSdms') ||
                       document.querySelector('input[name="athlete_sdms"]');
    const selectedDiv = document.getElementById('selectedAthlete');
    if (hiddenInput) {
        hiddenInput.value = athlete.sdms;
    }
    if (selectedDiv) {
        selectedDiv.innerHTML = `
            Selected: <strong>${athlete.sdms}</strong> - ${athlete.name} (${athlete.npc})
            <span class="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${athlete.class}</span>
        `;
    }
    input.value = '';
    resultsDiv.classList.add('hidden');
    checkClassCompatibility(athlete);
}
function checkClassCompatibility(athlete) {
    const gameClassesElement = document.querySelector('[data-game-classes]');
    if (!gameClassesElement) return;
    const gameClasses = gameClassesElement.dataset.gameClasses.split(',').map(c => c.trim());
    const selectedDiv = document.getElementById('selectedAthlete');
    if (!gameClasses.includes(athlete.class) && selectedDiv) {
        selectedDiv.innerHTML += `
            <div class="mt-2 p-2 bg-yellow-100 border border-yellow-400 text-yellow-700 rounded">
                <i class="fas fa-exclamation-triangle mr-1"></i>
                Warning: Athlete class ${athlete.class} not in event classes: ${gameClasses.join(', ')}
            </div>
        `;
    }
}
function initResultValidation() {
    const resultInputs = document.querySelectorAll('input[name="value"]');
    resultInputs.forEach(input => {
        const isFieldEvent = input.dataset.eventType === 'field';
        input.addEventListener('input', function() {
            validatePerformance(this, isFieldEvent);
        });
        input.addEventListener('blur', function() {
            validatePerformance(this, isFieldEvent);
        });
    });
}
function validatePerformance(input, isFieldEvent) {
    const value = input.value.trim();
    const specialValues = ['DNS', 'DNF', 'DQ', 'NM', 'O', 'X', '-'];
    input.classList.remove('border-red-500', 'border-green-500');
    if (specialValues.includes(value.toUpperCase())) {
        input.classList.add('border-green-500');
        return true;
    }
    let isValid = false;
    if (isFieldEvent) {
        isValid = /^\d+(\.\d{1,2})?$/.test(value);
    } else {
        isValid = /^(\d{1,2}:)?\d{1,2}\.\d{2}$/.test(value);
    }
    if (isValid) {
        input.classList.add('border-green-500');
    } else if (value) {
        input.classList.add('border-red-500');
    }
    return isValid;
}
function initStatusUpdates() {
    const statusSelects = document.querySelectorAll('select[name="status"]');
    statusSelects.forEach(select => {
        select.addEventListener('change', function() {
            const form = this.closest('form');
            if (form && form.dataset.autoSubmit === 'true') {
                form.submit();
            }
        });
    });
}
function initAttemptsHandling() {
    const attemptsInputs = document.querySelectorAll('input[name^="attempts-"]');
    attemptsInputs.forEach(input => {
        input.addEventListener('input', function() {
            updateBestAttempt();
        });
    });
}
function updateBestAttempt() {
    const attemptsInputs = document.querySelectorAll('input[name^="attempts-"]');
    const performanceInput = document.querySelector('input[name="value"]');
    if (!performanceInput) return;
    let bestValue = 0;
    let bestAttempt = '';
    attemptsInputs.forEach(input => {
        const value = input.value.trim();
        if (value && !['X', '-', 'FOUL'].includes(value.toUpperCase())) {
            const numValue = parseFloat(value);
            if (!isNaN(numValue) && numValue > bestValue) {
                bestValue = numValue;
                bestAttempt = value;
            }
        }
    });
    if (bestAttempt && !performanceInput.value) {
        performanceInput.value = bestAttempt;
        validatePerformance(performanceInput, true);
    }
}
function toggleAttempts(resultId) {
    const attemptsDiv = document.getElementById(`attempts-${resultId}`);
    if (attemptsDiv) {
        attemptsDiv.classList.toggle('hidden');
        const icon = document.querySelector(`[onclick="toggleAttempts(${resultId})"] i`);
        if (icon) {
            if (attemptsDiv.classList.contains('hidden')) {
                icon.className = 'fas fa-eye';
            } else {
                icon.className = 'fas fa-eye-slash';
            }
        }
    }
}
function selectFromStartList(sdms, name) {
    const hiddenInput = document.querySelector('input[name="athlete_sdms"]');
    const selectedDiv = document.getElementById('selectedAthlete');
    if (hiddenInput) {
        hiddenInput.value = sdms;
    }
    if (selectedDiv) {
        selectedDiv.innerHTML = `Selected: <strong>${sdms}</strong> - ${name}`;
    }
    const searchInput = document.querySelector('.athlete-search');
    if (searchInput) {
        searchInput.value = '';
    }
    const resultsDiv = document.querySelector('.athlete-search + div');
    if (resultsDiv) {
        resultsDiv.classList.add('hidden');
    }
}
function initAutoSave() {
    const forms = document.querySelectorAll('form[data-autosave]');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                saveFormData(form);
            });
        });
    });
}
function saveFormData(form) {
    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    localStorage.setItem(`form_${form.id}`, JSON.stringify(data));
}
function loadFormData(form) {
    const savedData = localStorage.getItem(`form_${form.id}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        for (let [key, value] of Object.entries(data)) {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }
    }
}
function selectAllResults(checkbox) {
    const checkboxes = document.querySelectorAll('input[name="selected_results[]"]');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
}
function bulkUpdateStatus(status) {
    const selected = document.querySelectorAll('input[name="selected_results[]"]:checked');
    if (selected.length === 0) {
        alert('Please select at least one result');
        return;
    }
    if (confirm(`Update status to "${status}" for ${selected.length} result(s)?`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/admin/results/bulk-update';
        const statusInput = document.createElement('input');
        statusInput.type = 'hidden';
        statusInput.name = 'status';
        statusInput.value = status;
        form.appendChild(statusInput);
        selected.forEach(checkbox => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'result_ids[]';
            input.value = checkbox.value;
            form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
    }
}
document.addEventListener('click', function(e) {
    const searchInputs = document.querySelectorAll('.athlete-search');
    searchInputs.forEach(input => {
        const resultsDiv = input.nextElementSibling;
        if (!input.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.classList.add('hidden');
        }
    });
});
function showValidationError(input, message) {
    const existingError = input.parentNode.querySelector('.validation-error');
    if (existingError) {
        existingError.remove();
    }
    const errorDiv = document.createElement('div');
    errorDiv.className = 'validation-error text-red-500 text-sm mt-1';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
    input.classList.add('border-red-500');
}
function clearValidationError(input) {
    const errorDiv = input.parentNode.querySelector('.validation-error');
    if (errorDiv) {
        errorDiv.remove();
    }
    input.classList.remove('border-red-500');
}