// Content script - runs on ToS pages
console.log('ToS Risk Detector: Content script loaded');

const API_URL = 'http://localhost:8000';
let analysisResults = null;

// Extract text from page
function extractPageText() {
    // Get main content area (try common selectors)
    const selectors = [
        'main',
        'article',
        '[role="main"]',
        '.content',
        '#content',
        'body'
    ];
    
    let contentElement = null;
    for (const selector of selectors) {
        contentElement = document.querySelector(selector);
        if (contentElement) break;
    }
    
    if (!contentElement) {
        contentElement = document.body;
    }
    
    // Extract text from paragraphs
    const paragraphs = contentElement.querySelectorAll('p, li, div.clause, div.section');
    const clauses = [];
    const seenTexts = new Set(); // Track seen text to avoid duplicates
    
    paragraphs.forEach(p => {
        const text = p.textContent.trim();
        // Filter: minimum 50 chars, maximum 1500 chars (avoid entire sections)
        if (text.length > 50 && text.length < 1500) {
            // Skip if we've already seen this exact text (prevents duplicates from nested elements)
            if (seenTexts.has(text)) {
                return;
            }
            
            seenTexts.add(text);
            clauses.push({
                text: text,
                element: p
            });
        }
    });
    
    // Don't limit clauses - we'll process them progressively
    console.log(`Extracted ${clauses.length} potential clauses (filtered ${paragraphs.length - clauses.length} duplicates/invalid)`);
    return clauses;
}

// Send clauses to API for classification (with chunking for large batches)
async function classifyClauses(clauses) {
    try {
        const clauseTexts = clauses.map(c => c.text);
        
        // If too many clauses, process in chunks to avoid timeout
        const CHUNK_SIZE = 5; // Process 5 clauses at a time (reduced for slower inference)
        const results = [];
        
        if (clauseTexts.length > CHUNK_SIZE) {
            console.log(`Processing ${clauseTexts.length} clauses in chunks of ${CHUNK_SIZE}...`);
            
            for (let i = 0; i < clauseTexts.length; i += CHUNK_SIZE) {
                const chunk = clauseTexts.slice(i, i + CHUNK_SIZE);
                console.log(`Processing chunk ${Math.floor(i/CHUNK_SIZE) + 1}/${Math.ceil(clauseTexts.length/CHUNK_SIZE)}...`);
                
                // Update loading message
                updateLoadingMessage(`Analyzing clauses ${i + 1}-${Math.min(i + CHUNK_SIZE, clauseTexts.length)} of ${clauseTexts.length}...`);
                
                const response = await fetch(`${API_URL}/classify-batch-with-attention`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clauses: chunk
                    }),
                    signal: AbortSignal.timeout(60000) // 60 second timeout per chunk (increased)
                });
                
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                
                const chunkData = await response.json();
                // API returns {status: "success", data: {results: [...]}}
                const chunkResults = chunkData.data ? chunkData.data.results : chunkData.results;
                results.push(...chunkResults);
            }
            
            return results;
        } else {
            // Small batch, process all at once
            const response = await fetch(`${API_URL}/classify-batch-with-attention`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    clauses: clauseTexts
                }),
                signal: AbortSignal.timeout(60000) // 60 second timeout
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const responseData = await response.json();
            // API returns {status: "success", data: {results: [...]}}
            return responseData.data ? responseData.data.results : responseData.results;
        }
        
    } catch (error) {
        console.error('Classification error:', error);
        if (error.name === 'TimeoutError') {
            showError('Request timed out. The page may have too many clauses. Try a simpler ToS page.');
        } else if (error.message.includes('Failed to fetch')) {
            showError('Cannot connect to API. Make sure the server is running at localhost:8000');
        }
        return null;
    }
}

// Update loading message
function updateLoadingMessage(message) {
    const loader = document.getElementById('tos-loader');
    if (loader) {
        const messageEl = loader.querySelector('p');
        if (messageEl) {
            messageEl.textContent = message;
        }
    }
}

// Highlight risky clauses on page
function highlightClauses(clauses, classifications, appendMode = false) {
    let highRiskCount = 0;
    let mediumRiskCount = 0;
    let lowRiskCount = 0;
    
    // If appending, get current counts from stored results
    if (appendMode && analysisResults) {
        highRiskCount = analysisResults.highRisk;
        mediumRiskCount = analysisResults.mediumRisk;
        lowRiskCount = analysisResults.lowRisk;
    }
    
    clauses.forEach((clause, index) => {
        const classification = classifications[index];
        const element = clause.element;
        
        // Skip if already processed (prevent duplicate highlighting)
        if (element.classList.contains('tos-risky-clause') || element.classList.contains('tos-safe-clause')) {
            console.log('Skipping already processed element');
            return;
        }
        
        // Skip if no risks detected
        if (!classification.is_risky) {
            element.classList.add('tos-safe-clause');
            lowRiskCount++;
            return;
        }
        
        // Determine risk level based on number of risks
        const riskCount = classification.risks_detected.length;
        let riskLevel = 'low';
        
        if (riskCount >= 3) {
            riskLevel = 'high';
            highRiskCount++;
        } else if (riskCount >= 2) {
            riskLevel = 'medium';
            mediumRiskCount++;
        } else {
            riskLevel = 'low';
            lowRiskCount++;
        }
        
        // Add highlighting with fade-in animation
        element.classList.add('tos-risky-clause');
        element.classList.add(`tos-risk-${riskLevel}`);
        if (appendMode) {
            element.style.animation = 'fadeIn 0.5s ease-in';
        }
        element.setAttribute('data-risk-level', riskLevel);
        element.setAttribute('data-risk-count', riskCount);
        
        // Create tooltip
        const tooltip = createTooltip(classification);
        element.appendChild(tooltip);
        
        // Add click handler
        element.style.cursor = 'pointer';
        element.addEventListener('click', () => {
            showRiskDetails(classification);
        });
        
        // Add hover effect
        element.addEventListener('mouseenter', () => {
            tooltip.style.display = 'block';
        });
        element.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });
    });
    
    // Update badge
    updateBadge(highRiskCount, mediumRiskCount, lowRiskCount);
    
    // Store or update results
    if (!appendMode || !analysisResults) {
        // Initial results
        analysisResults = {
            highRisk: highRiskCount,
            mediumRisk: mediumRiskCount,
            lowRisk: lowRiskCount,
            total: clauses.length,
            classifications: classifications
        };
    } else {
        // Append to existing results
        analysisResults.highRisk = highRiskCount;
        analysisResults.mediumRisk = mediumRiskCount;
        analysisResults.lowRisk = lowRiskCount;
        analysisResults.total += clauses.length;
        analysisResults.classifications.push(...classifications);
    }
    
    // Send to background script
    chrome.runtime.sendMessage({
        action: 'updateResults',
        results: analysisResults
    });
}

// Create tooltip element
function createTooltip(classification) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tos-tooltip';
    
    let html = '<div class="tos-tooltip-content">';
    html += '<strong>⚠️ Risks Detected:</strong><br>';
    
    classification.risks_detected.forEach(risk => {
        const confidence = (risk.confidence * 100).toFixed(0);
        html += `<div class="risk-item">`;
        html += `  <span class="risk-name">${risk.risk_type}</span>`;
        html += `  <span class="risk-confidence">${confidence}%</span>`;
        html += `</div>`;
    });
    
    html += '</div>';
    tooltip.innerHTML = html;
    tooltip.style.display = 'none';
    
    return tooltip;
}

// Show detailed risk information
function showRiskDetails(classification) {
    const modal = document.createElement('div');
    modal.className = 'tos-modal';
    
    let html = '<div class="tos-modal-content">';
    html += '<span class="tos-modal-close">&times;</span>';
    html += '<h2>Risk Analysis</h2>';
    
    html += '<div class="risk-section">';
    html += '<h3>Detected Risks:</h3>';
    classification.risks_detected.forEach(risk => {
        html += `<div class="risk-detail">`;
        html += `  <h4>${risk.risk_type}</h4>`;
        html += `  <p>Confidence: ${(risk.confidence * 100).toFixed(1)}%</p>`;
        
        // Risk Explanation
        if (risk.explanation) {
            html += `  <div class="llm-explanation">`;
            html += `    <div class="llm-label">💡 What This Means:</div>`;
            html += `    <p>${risk.explanation}</p>`;
            html += `  </div>`;
        } else {
            // Fallback to hardcoded explanation (shouldn't happen)
            html += `  <p class="risk-explanation">${getRiskExplanation(risk.risk_type)}</p>`;
        }
        
        html += `</div>`;
    });
    html += '</div>';
    
    // NEW: XAI Attention Visualization
    if (classification.attention_explanation) {
        const attention = classification.attention_explanation;
        
        html += '<div class="attention-section">';
        html += '<h3>🔍 Why This Was Detected (XAI)</h3>';
        
        // Heatmap visualization
        html += '<div class="attention-heatmap">';
        html += '<p class="heatmap-label">Word Importance Heatmap:</p>';
        html += '<div class="heatmap-text">';
        
        attention.heatmap_data.forEach(item => {
            const intensity = item.normalized;
            const color = getHeatmapColor(intensity);
            const fontSize = 14 + (intensity * 6);  // 14-20px
            
            html += `
                <span class="heatmap-word" 
                      style="background-color: ${color}; 
                             font-size: ${fontSize}px;"
                      data-importance="${item.importance.toFixed(3)}"
                      title="Importance: ${item.importance.toFixed(3)}">
                    ${item.word}
                </span>
            `;
        });
        
        html += '</div></div>';
        
        // Top influential words
        if (attention.top_words && attention.top_words.length > 0) {
            html += '<div class="top-words">';
            html += '<h4>Most Influential Words:</h4>';
            html += '<ol>';
            attention.top_words.slice(0, 5).forEach(word => {
                const percentage = (word.importance * 100).toFixed(1);
                html += `
                    <li>
                        <strong>"${word.word}"</strong>
                        <span class="importance-bar">
                            <span style="width: ${percentage}%"></span>
                        </span>
                        <span class="importance-value">${percentage}%</span>
                    </li>
                `;
            });
            html += '</ol></div>';
        }
        
        html += '</div>';
    }
    
    html += '</div>';
    modal.innerHTML = html;
    
    document.body.appendChild(modal);
    
    // Close button
    modal.querySelector('.tos-modal-close').addEventListener('click', () => {
        modal.remove();
    });
    
    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Helper function for heatmap colors
function getHeatmapColor(intensity) {
    // Gradient from light yellow (low) to dark red (high)
    if (intensity < 0.3) {
        return `rgba(255, 255, 200, ${0.3 + intensity})`;  // Light yellow
    } else if (intensity < 0.6) {
        return `rgba(255, 200, 100, ${0.5 + intensity})`;  // Orange
    } else {
        return `rgba(255, 100, 100, ${0.6 + intensity})`;  // Red
    }
}

// Get risk explanation
function getRiskExplanation(category) {
    const explanations = {
        'Limitation of liability': 'The service limits its responsibility for damages or losses you may incur.',
        'Unilateral termination': 'The service can terminate your account without notice or cause.',
        'Unilateral change': 'The service can change terms at any time without your consent.',
        'Content removal': 'The service can remove your content without explanation.',
        'Contract by using': 'Simply using the service means you agree to all terms.',
        'Choice of law': 'Disputes are governed by laws that may not be in your jurisdiction.',
        'Jurisdiction': 'Legal disputes must be resolved in a specific location, possibly far from you.',
        'Arbitration': 'You waive your right to sue in court and must use arbitration instead.'
    };
    
    return explanations[category] || 'This clause may contain unfair terms.';
}

// Update extension badge
function updateBadge(high, medium, low) {
    let badgeText = '';
    let badgeColor = '#44ff44'; // Green
    
    if (high > 0) {
        badgeText = '🔴';
        badgeColor = '#ff4444';
    } else if (medium > 0) {
        badgeText = '🟡';
        badgeColor = '#ffaa00';
    } else {
        badgeText = '🟢';
        badgeColor = '#44ff44';
    }
    
    chrome.runtime.sendMessage({
        action: 'updateBadge',
        text: badgeText,
        color: badgeColor
    });
}

// Main analysis function with progressive loading
async function analyzeToS() {
    console.log('Starting ToS analysis...');
    
    // Show loading indicator
    showLoadingIndicator();
    
    // Extract clauses
    const clauses = extractPageText();
    
    if (clauses.length === 0) {
        console.log('No clauses found on page');
        hideLoadingIndicator();
        return;
    }
    
    console.log(`Total clauses to analyze: ${clauses.length}`);
    
    // Split into initial batch (25) and remaining
    const INITIAL_BATCH_SIZE = 25;
    const initialClauses = clauses.slice(0, INITIAL_BATCH_SIZE);
    const remainingClauses = clauses.slice(INITIAL_BATCH_SIZE);
    
    // Classify initial batch with loading animation
    updateLoadingMessage(`Analyzing first ${initialClauses.length} clauses...`);
    const initialClassifications = await classifyClauses(initialClauses);
    
    if (!initialClassifications) {
        console.error('Classification failed');
        hideLoadingIndicator();
        showError('Failed to analyze ToS. Make sure the API is running.');
        return;
    }
    
    // Highlight initial batch
    highlightClauses(initialClauses, initialClassifications);
    
    // Hide loading indicator
    hideLoadingIndicator();
    console.log('Initial batch complete!');
    
    // Process remaining clauses in background if any
    if (remainingClauses.length > 0) {
        console.log(`Processing ${remainingClauses.length} more clauses in background...`);
        showBackgroundProgress(remainingClauses.length);
        
        // Process remaining clauses in chunks
        const CHUNK_SIZE = 5;
        let processedCount = 0;
        
        for (let i = 0; i < remainingClauses.length; i += CHUNK_SIZE) {
            const chunk = remainingClauses.slice(i, i + CHUNK_SIZE);
            
            // Classify chunk
            const chunkClassifications = await classifyClauses(chunk);
            
            if (chunkClassifications) {
                // Highlight this chunk
                highlightClauses(chunk, chunkClassifications, true); // true = append mode
                
                processedCount += chunk.length;
                updateBackgroundProgress(processedCount, remainingClauses.length);
            }
        }
        
        hideBackgroundProgress();
        console.log('All clauses analyzed!');
    }
}

// Show loading indicator
function showLoadingIndicator() {
    const loader = document.createElement('div');
    loader.id = 'tos-loader';
    loader.innerHTML = `
        <div class="tos-loader-content">
            <div class="spinner"></div>
            <p>Analyzing Terms of Service...</p>
        </div>
    `;
    document.body.appendChild(loader);
}

// Hide loading indicator
function hideLoadingIndicator() {
    const loader = document.getElementById('tos-loader');
    if (loader) {
        loader.remove();
    }
}

// Background progress indicator functions
function showBackgroundProgress(totalRemaining) {
    const progress = document.createElement('div');
    progress.id = 'tos-background-progress';
    progress.innerHTML = `
        <div class="tos-progress-content">
            <div class="tos-progress-icon">⚡</div>
            <div class="tos-progress-text">
                <strong>Analyzing more clauses...</strong>
                <span id="tos-progress-count">0 / ${totalRemaining}</span>
            </div>
        </div>
    `;
    document.body.appendChild(progress);
}

function updateBackgroundProgress(processed, total) {
    const countEl = document.getElementById('tos-progress-count');
    if (countEl) {
        countEl.textContent = `${processed} / ${total}`;
    }
}

function hideBackgroundProgress() {
    const progress = document.getElementById('tos-background-progress');
    if (progress) {
        progress.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => progress.remove(), 300);
    }
}

// Show error message
function showError(message) {
    const error = document.createElement('div');
    error.className = 'tos-error';
    error.innerHTML = `
        <div class="tos-error-content">
            <h3>⚠️ Error</h3>
            <p>${message}</p>
            <button onclick="this.parentElement.parentElement.remove()">Close</button>
        </div>
    `;
    document.body.appendChild(error);
    
    setTimeout(() => {
        error.remove();
    }, 5000);
}

// Auto-run analysis when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', analyzeToS);
} else {
    analyzeToS();
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getResults') {
        sendResponse(analysisResults);
    } else if (request.action === 'reanalyze') {
        analyzeToS();
        sendResponse({ success: true });
    }
});
