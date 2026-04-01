// Claussifier Frontend JavaScript

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const clauseInput = document.getElementById('clauseInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');
const riskStatus = document.getElementById('riskStatus');
const risksDetected = document.getElementById('risksDetected');
const safeCategories = document.getElementById('safeCategories');

// Example clause buttons
const exampleButtons = document.querySelectorAll('.example-btn');

// Event Listeners
analyzeBtn.addEventListener('click', analyzeClause);
clearBtn.addEventListener('click', clearInput);
clauseInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        analyzeClause();
    }
});

// Example buttons
exampleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        clauseInput.value = btn.dataset.clause;
        analyzeClause();
    });
});

// Model selector
const modelSelect = document.getElementById('modelSelect');
modelSelect.addEventListener('change', async () => {
    const selectedModel = modelSelect.value;
    
    try {
        // Show loading state
        document.getElementById('modelName').textContent = 'Switching...';
        document.getElementById('modelF1').textContent = '--';
        document.getElementById('modelPrecision').textContent = '--';
        
        // Call switch-model endpoint
        const response = await fetch(`${API_BASE_URL}/switch-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ model_name: selectedModel })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Reload model info
            await loadModelInfo();
            console.log('Model switched successfully:', result.current_model);
        } else {
            alert('Failed to switch model');
        }
    } catch (error) {
        console.error('Error switching model:', error);
        alert('Error switching model. Please try again.');
    }
});

// Load model info on page load
async function loadModelInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/model-info`);
        const result = await response.json();
        
        if (result.status === 'success' && result.data) {
            const data = result.data;
            document.getElementById('modelName').textContent = data.model_name || 'Legal-BERT Risk Detector';
            document.getElementById('modelF1').textContent = data.f1_score || '--';
            document.getElementById('modelPrecision').textContent = data.precision || '--';
            
            // Sync dropdown with backend's current model
            if (result.current_model) {
                modelSelect.value = result.current_model;
            }
        }
    } catch (error) {
        console.error('Failed to load model info:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadModelInfo();
});

// Functions
async function analyzeClause() {
    const clause = clauseInput.value.trim();
    
    // Validation
    if (!clause) {
        showError('Please enter a clause to analyze.');
        return;
    }
    
    if (clause.length < 10) {
        showError('Clause is too short. Please enter at least 10 characters.');
        return;
    }
    
    // Show loading
    showLoading();
    
    try {
        // Call API
        const response = await fetch(`${API_BASE_URL}/classify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                clause: clause,
                return_all_scores: false
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Classification failed');
        }
        
        const data = await response.json();
        
        // Display results
        displayResults(data.data);
        
    } catch (error) {
        console.error('Error:', error);
        
        if (error.message.includes('Failed to fetch')) {
            showError(
                'Cannot connect to API server. Please make sure the backend is running at ' + API_BASE_URL,
                'Connection Error'
            );
        } else {
            showError(error.message, 'Classification Error');
        }
    } finally {
        hideLoading();
    }
}

function displayResults(result) {
    // Hide error, show results
    errorMessage.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Display summary cards
    displaySummaryCards(result);
    
    // Display risk status (hidden by CSS, but kept for compatibility)
    displayRiskStatus(result.is_risky);
    
    // Display detected risks with attention data
    displayRisks(result.risks_detected, result.attention_explanation);
    
    // Hide safe categories section
    safeCategories.style.display = 'none';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function displaySummaryCards(result) {
    // Remove existing summary cards if any
    const existingSummary = resultsSection.querySelector('.summary-cards');
    if (existingSummary) {
        existingSummary.remove();
    }
    
    const summaryHTML = `
        <div class="summary-cards">
            <div class="summary-card ${result.is_risky ? 'status-risky' : 'status-safe'}">
                <div class="summary-card-label">Overall Status</div>
                <div class="summary-card-value">${result.is_risky ? 'RISKY' : 'SAFE'}</div>
                <div class="summary-card-subtitle">${result.is_risky ? 'Risks Detected' : 'No Risks Found'}</div>
            </div>
            <div class="summary-card risks-count">
                <div class="summary-card-label">Risks Found</div>
                <div class="summary-card-value">${result.risks_detected.length}</div>
                <div class="summary-card-subtitle">${result.risks_detected.length === 1 ? 'Risk Type' : 'Risk Types'}</div>
            </div>
        </div>
    `;
    
    // Insert summary cards at the beginning of results section
    const resultsH2 = resultsSection.querySelector('h2');
    if (resultsH2) {
        resultsH2.insertAdjacentHTML('afterend', summaryHTML);
    }
}

function displayRiskStatus(isRisky) {
    if (isRisky) {
        riskStatus.className = 'risk-status risky';
        riskStatus.innerHTML = `
            <span class="status-icon">⚠️</span>
            <div>RISKY CLAUSE DETECTED</div>
        `;
    } else {
        riskStatus.className = 'risk-status safe';
        riskStatus.innerHTML = `
            <span class="status-icon">✅</span>
            <div>NO RISKS DETECTED</div>
        `;
    }
}

function displayRisks(risks, attentionExplanation) {
    if (risks.length === 0) {
        risksDetected.style.display = 'none';
        return;
    }
    
    risksDetected.style.display = 'block';
    
    // Function to determine severity based on confidence
    function getSeverity(confidence) {
        if (confidence >= 0.90) return { level: 'high', label: 'High' };
        if (confidence >= 0.70) return { level: 'medium', label: 'Medium' };
        return { level: 'low', label: 'Low' };
    }
    
    // Fetch dynamic explanation (streaming)
    async function fetchStreamingExplanation(clause, riskType, explanationTextEl) {
        try {
            const response = await fetch(`${API_BASE_URL}/explain`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ clause, risk_type: riskType })
            });
            
            const contentType = response.headers.get('content-type') || '';
            
            if (contentType.includes('text/event-stream')) {
                // Streaming response — read tokens word-by-word
                explanationTextEl.textContent = '';
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep incomplete line in buffer
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.token) {
                                    explanationTextEl.textContent += data.token;
                                }
                                if (data.done) {
                                    return { source: 'gemma3n', text: explanationTextEl.textContent };
                                }
                            } catch (e) { /* skip malformed line */ }
                        }
                    }
                }
                return { source: 'gemma3n', text: explanationTextEl.textContent };
            } else {
                // JSON fallback (static explanation)
                const data = await response.json();
                explanationTextEl.textContent = data.explanation;
                return { source: data.source || 'static', text: data.explanation };
            }
        } catch (error) {
            console.error('Failed to fetch explanation:', error);
            return { source: 'static', text: explanationTextEl.textContent };
        }
    }
    
    // Function to get distinct heatmap styling based on intensity
    function getHeatmapStyle(intensity) {
        if (intensity < 0.15) {
            return { bg: 'transparent', fg: 'inherit', weight: 'normal', size: '0.95em' };
        } else if (intensity < 0.35) {
            return { bg: '#fff9c4', fg: '#333', weight: 'normal', size: '0.95em' }; // Light Yellow
        } else if (intensity < 0.6) {
            return { bg: '#ffe082', fg: '#856404', weight: '500', size: '1.0em' };  // Amber
        } else if (intensity < 0.8) {
            return { bg: '#ffb74d', fg: '#541f00', weight: '600', size: '1.05em' }; // Orange
        } else if (intensity < 0.95) {
            return { bg: '#f4511e', fg: '#fff', weight: '700', size: '1.1em' };   // Deep Orange
        } else {
            return { bg: '#d32f2f', fg: '#fff', weight: 'bold', size: '1.15em' }; // Red
        }
    }
    
    // Build heatmap HTML once (shared across all risks)
    let heatmapHTML = '';
    if (attentionExplanation) {
        const attention = attentionExplanation;
        
        // Heatmap visualization
        heatmapHTML += `<div class="attention-heatmap">`;
        heatmapHTML += `<div class="heatmap-label">🔍 Word Importance Heatmap</div>`;
        heatmapHTML += `<div class="heatmap-text">`;
        
        attention.heatmap_data.forEach(item => {
            const style = getHeatmapStyle(item.normalized);
            heatmapHTML += `<span class="heatmap-word" 
                                 style="background-color: ${style.bg}; color: ${style.fg}; font-weight: ${style.weight}; font-size: ${style.size}; margin: 3px 2px;"
                                 title="Importance: ${item.importance.toFixed(3)}">
                                ${item.word}
                            </span>`;
        });
        
        heatmapHTML += `</div></div>`;
        
        // Top words list
        if (attention.top_words && attention.top_words.length > 0) {
            heatmapHTML += `<div class="top-words">`;
            heatmapHTML += `<h4>Most Influential Words:</h4>`;
            heatmapHTML += `<ol>`;
            
            attention.top_words.slice(0, 5).forEach(word => {
                const percentage = (word.importance * 100).toFixed(1);
                heatmapHTML += `<li>
                    <strong>"${word.word}"</strong>
                    <span class="importance-bar">
                        <span style="width: ${percentage}%"></span>
                    </span>
                    <span class="importance-value">${percentage}%</span>
                </li>`;
            });
            
            heatmapHTML += `</ol></div>`;
        }
    }
    
    // Store the clause text for on-demand explanation
    const currentClause = clauseInput.value.trim();
    
    const risksHTML = `
        <h3>⚠️ Identified Risks (${risks.length})</h3>
        ${risks.map((risk, index) => {
            const severity = getSeverity(risk.confidence);
            const confidencePercent = (risk.confidence * 100).toFixed(1);
            const explanation = risk.explanation || '';
            const riskId = `risk-${index}`;
            
            return `
                <div class="risk-item" data-clause="${encodeURIComponent(currentClause)}" data-risk-type="${risk.risk_type}">
                    <div class="risk-item-header">
                        <div class="risk-name">${risk.risk_type}</div>
                        <div class="risk-confidence">
                            <span class="confidence-percentage">${confidencePercent}%</span>
                            <span class="severity-badge severity-${severity.level}">${severity.label} Risk</span>
                        </div>
                    </div>
                    <div class="confidence-bar-container">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${risk.confidence * 100}%"></div>
                        </div>
                    </div>
                    <button class="toggle-explanation" data-risk-id="${riskId}">
                        <span class="toggle-icon">▼</span>
                        <span class="toggle-text">What This Means</span>
                    </button>
                    <div class="risk-explanation" id="${riskId}">
                        <div class="explanation-label">
                            💡 Explanation
                        </div>
                        <div class="explanation-text" id="${riskId}-text">${explanation}</div>
                        <div class="explanation-loading" id="${riskId}-loading" style="display:none;">
                            <span class="loading-dots">Generating AI explanation<span>.</span><span>.</span><span>.</span></span>
                        </div>
                    </div>
                </div>
            `;
        }).join('')}
        
        ${heatmapHTML}
    `;
    
    risksDetected.innerHTML = risksHTML;
    
    // Add click handlers for toggle buttons (with streaming explanation)
    document.querySelectorAll('.toggle-explanation').forEach(button => {
        button.addEventListener('click', async function() {
            const riskId = this.getAttribute('data-risk-id');
            const explanationDiv = document.getElementById(riskId);
            const explanationText = document.getElementById(`${riskId}-text`);
            const explanationLoading = document.getElementById(`${riskId}-loading`);
            const riskItem = this.closest('.risk-item');
            
            // Toggle expanded state
            this.classList.toggle('expanded');
            explanationDiv.classList.toggle('expanded');
            
            // Update button text
            const toggleText = this.querySelector('.toggle-text');
            if (this.classList.contains('expanded')) {
                toggleText.textContent = 'Hide Explanation';
                
                // Fetch dynamic explanation on first expand (if not already fetched)
                if (!explanationDiv.dataset.fetched) {
                    explanationDiv.dataset.fetched = 'loading';
                    
                    // Show loading indicator
                    explanationLoading.style.display = 'block';
                    
                    // Get clause and risk type from data attributes
                    const clause = decodeURIComponent(riskItem.dataset.clause);
                    const riskType = riskItem.dataset.riskType;
                    
                    // Stream explanation from Gemma 3n
                    await fetchStreamingExplanation(clause, riskType, explanationText);
                    
                    explanationLoading.style.display = 'none';
                    explanationDiv.dataset.fetched = 'done';
                }
            } else {
                toggleText.textContent = 'What This Means';
            }
        });
    });
}

function displaySafeCategories(safeCategoriesList) {
    if (safeCategoriesList.length === 0) {
        safeCategories.style.display = 'none';
        return;
    }
    
    safeCategories.style.display = 'block';
    
    const safeHTML = `
        <h3>✓ Safe Categories (${safeCategoriesList.length})</h3>
        <div class="safe-grid">
            ${safeCategoriesList.map(category => `
                <div class="safe-item">
                    <span class="safe-icon">✓</span>
                    ${category}
                </div>
            `).join('')}
        </div>
    `;
    
    safeCategories.innerHTML = safeHTML;
}

function showLoading() {
    analyzeBtn.disabled = true;
    loadingIndicator.style.display = 'block';
    resultsSection.style.display = 'none';
    errorMessage.style.display = 'none';
}

function hideLoading() {
    analyzeBtn.disabled = false;
    loadingIndicator.style.display = 'none';
}

function showError(message, title = 'Error') {
    errorMessage.style.display = 'block';
    errorMessage.innerHTML = `
        <strong>${title}</strong>
        <p>${message}</p>
    `;
    resultsSection.style.display = 'none';
    
    // Scroll to error
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearInput() {
    clauseInput.value = '';
    resultsSection.style.display = 'none';
    errorMessage.style.display = 'none';
    clauseInput.focus();
}

// Check API health on load
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.status !== 'healthy') {
            console.warn('API is not healthy:', data);
        } else {
            console.log('✓ API is healthy and ready');
        }
    } catch (error) {
        console.error('Cannot connect to API:', error);
        showError(
            `Cannot connect to the API server at ${API_BASE_URL}. Please make sure the backend is running.`,
            'Connection Error'
        );
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Claussifier Frontend Loaded');
    checkAPIHealth();
    
    // Focus on input
    clauseInput.focus();
});
