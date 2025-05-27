// Fonction pour construire les paramètres de requête
function buildQueryParams(filters) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value && value.trim()) {
            params.append(key, value.trim());
        }
    });
    return params.toString();
}

// Fonction pour collecter les filtres d'un élément
function collectFilters(element) {
    const filters = {};
    const filterInputs = element.parentElement.querySelectorAll('[data-filter]');
    
    filterInputs.forEach(input => {
        const filterName = input.getAttribute('data-filter');
        const value = input.value;
        if (value && value.trim()) {
            filters[filterName] = value.trim();
        }
    });
    
    return filters;
}

// Fonction pour afficher le statut
function showStatus(button, type, message) {
    const statusDiv = button.parentElement.parentElement.querySelector('.status');
    statusDiv.className = `status ${type}`;
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
}

// Fonction générique pour exécuter une requête
async function executeApiRequest(url, button, outputPath) {
    const apiKey = document.getElementById('apiKey').value;
    if (!apiKey) {
        showStatus(button, 'error', 'Veuillez entrer votre clé API');
        return;
    }

    button.disabled = true;
    showStatus(button, 'loading', 'Exécution en cours...');

    try {
        const response = await fetch(url, {
            headers: {
                'X-Auth-Token': apiKey,
                'Accept': 'application/json'
            },
            mode: 'cors'
        });

        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status} - ${response.statusText}`);
        }

        const data = await response.json();
        
        // Téléchargement automatique du fichier JSON
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const downloadUrl = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = outputPath || 'data.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);

        showStatus(button, 'success', `Données sauvegardées dans ${outputPath}. Téléchargement lancé!`);
        
        // Log pour debug
        console.log('Réponse API:', data);
        
    } catch (error) {
        console.error('Erreur:', error);
        showStatus(button, 'error', `Erreur: ${error.message}`);
    } finally {
        button.disabled = false;
    }
}

// Fonctions spécifiques pour chaque type de requête
function executeRequest(endpoint, button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}${endpoint}${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

function executeStandingsRequest(button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const competitionId = filters['competition-id'];
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    if (!competitionId) {
        showStatus(button, 'error', 'Veuillez sélectionner une compétition');
        return;
    }
    
    delete filters['competition-id'];
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}/competitions/${competitionId}/standings${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

function executeCompetitionMatchesRequest(button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const competitionId = filters['competition-id'];
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    if (!competitionId) {
        showStatus(button, 'error', 'Veuillez sélectionner une compétition');
        return;
    }
    
    delete filters['competition-id'];
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}/competitions/${competitionId}/matches${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

function executeCompetitionTeamsRequest(button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const competitionId = filters['competition-id'];
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    if (!competitionId) {
        showStatus(button, 'error', 'Veuillez sélectionner une compétition');
        return;
    }
    
    delete filters['competition-id'];
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}/competitions/${competitionId}/teams${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

function executeScorersRequest(button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const competitionId = filters['competition-id'];
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    if (!competitionId) {
        showStatus(button, 'error', 'Veuillez sélectionner une compétition');
        return;
    }
    
    delete filters['competition-id'];
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}/competitions/${competitionId}/scorers${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

function executeTeamMatchesRequest(button) {
    const baseUrl = document.getElementById('baseUrl').value;
    const filters = collectFilters(button);
    const teamId = filters['team-id'];
    const outputPath = button.parentElement.querySelector('.output-path').value;
    
    if (!teamId) {
        showStatus(button, 'error', 'Veuillez entrer un ID d\'équipe');
        return;
    }
    
    delete filters['team-id'];
    const queryString = buildQueryParams(filters);
    const url = `${baseUrl}/teams/${teamId}/matches${queryString ? '?' + queryString : ''}`;
    
    console.log('URL générée:', url);
    executeApiRequest(url, button, outputPath);
}

// Auto-remplissage et initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('Football Data API Client chargé');
    
    // Optionnel: pré-remplir certains champs
    const today = new Date().toISOString().split('T')[0];
    
    // Gestion des événements pour améliorer l'UX
    const apiKeyInput = document.getElementById('apiKey');
    apiKeyInput.addEventListener('input', function() {
        // Sauvegarder temporairement la clé API (attention à la sécurité en production)
        if (this.value.length > 10) {
            localStorage.setItem('temp_api_key', this.value);
        }
    });
    
    // Restaurer la clé API si elle existe
    const savedApiKey = localStorage.getItem('temp_api_key');
    if (savedApiKey) {
        apiKeyInput.value = savedApiKey;
    }
});