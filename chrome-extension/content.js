// Content script - runs on ToS pages
console.log('ToS Risk Detector: Content script loaded');

const API_URL = 'http://localhost:8000';
let analysisResults = null;

// --- PRIVACY & SECURITY MODULE ---

// Only allow data to be sent to local endpoints
const ALLOWED_API_ORIGINS = ['http://localhost', 'http://127.0.0.1'];

function isApiUrlSafe(url) {
    return ALLOWED_API_ORIGINS.some(origin => url.startsWith(origin));
}

// PII patterns to redact before sending text to the API
const PII_PATTERNS = [
    { regex: /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b/g, replacement: '[EMAIL_REDACTED]' },
    { regex: /\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b/g, replacement: '[SSN_REDACTED]' },
    { regex: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g, replacement: '[CARD_REDACTED]' },
    { regex: /\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g, replacement: '[PHONE_REDACTED]' },
    { regex: /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, replacement: '[IP_REDACTED]' },
];

// Redact PII from text before sending to API
function redactPII(text) {
    let sanitized = text;
    for (const { regex, replacement } of PII_PATTERNS) {
        sanitized = sanitized.replace(regex, replacement);
    }
    return sanitized;
}

// Elements/containers that may hold user-specific or editable content
const USER_CONTENT_SELECTORS = [
    'form',
    '[contenteditable="true"]',
    'textarea',
    'input',
    '[role="textbox"]',
    '.comment', '.comments', '.review', '.reviews',
    '.user-profile', '.account-info', '.profile',
    '[data-user]', '[data-account]'
];

// Check if element is inside a user-content/form area
function isUserContentArea(element) {
    for (const selector of USER_CONTENT_SELECTORS) {
        if (element.closest(selector)) {
            return true;
        }
    }
    // Check if element itself is editable
    if (element.isContentEditable) return true;
    return false;
}

// Verify the page is likely a legal/ToS document (not a user account page)
function isLikelyLegalPage() {
    const pageText = document.body.innerText.toLowerCase();
    const legalKeywords = [
        // Formal legal terms
        'terms of service', 'terms of use', 'terms and conditions',
        'privacy policy', 'user agreement', 'license agreement',
        'end user license', 'acceptable use', 'cookie policy',
        'data protection', 'intellectual property', 'limitation of liability',
        'governing law', 'arbitration', 'indemnification', 'disclaimer',
        // Common in modern/simplified ToS
        'reserve the right', 'we may terminate', 'cancellation policy',
        'refund', 'subscription', 'you agree not to',
        'prohibited content', 'terminate your account', 'at our sole discretion',
        'binding agreement', 'third-party', 'comply with'
    ];
    const matchCount = legalKeywords.filter(kw => pageText.includes(kw)).length;
    // Require at least 2 legal keywords to confirm this is a legal page
    return matchCount >= 2;
}

// Strip sensitive data from classification results before storage
function sanitizeResultsForStorage(results) {
    return {
        highRisk: results.highRisk,
        mediumRisk: results.mediumRisk,
        lowRisk: results.lowRisk,
        total: results.total,
        // Only store classification metadata, not raw clause text
        classifications: results.classifications.map(c => ({
            is_risky: c.is_risky,
            risks_detected: c.risks_detected.map(r => ({
                risk_type: r.risk_type,
                confidence: r.confidence
            })),
            safe_categories: c.safe_categories
            // Deliberately omit: clause (raw text), attention_explanation
        }))
    };
}

// --- END PRIVACY & SECURITY MODULE ---

// Selectors for navigation/TOC containers to exclude
const EXCLUDED_ANCESTORS = [
    'nav',
    'aside',
    'header',
    'footer',
    '[role="navigation"]',
    '[role="banner"]',
    '[role="contentinfo"]'
];

// Class/ID patterns indicating navigation or TOC elements
const NAV_TOC_PATTERNS = /\b(toc|table-of-content|table_of_content|tableofcontent|sidebar|side-bar|side-nav|sidenav|nav|menu|breadcrumb|footer|header)\b/i;

// Check if an element is inside a navigation/TOC container
function isInExcludedContainer(element) {
    // Check structural ancestors
    for (const selector of EXCLUDED_ANCESTORS) {
        if (element.closest(selector)) {
            return true;
        }
    }
    // Check class/id patterns on ancestors
    let el = element;
    while (el && el !== document.body) {
        const classAndId = (el.className || '') + ' ' + (el.id || '');
        if (NAV_TOC_PATTERNS.test(classAndId)) {
            return true;
        }
        el = el.parentElement;
    }
    return false;
}

// Check if a list item is primarily a navigation link (TOC entry)
function isNavLink(element) {
    if (element.tagName !== 'LI') return false;
    const links = element.querySelectorAll('a');
    if (links.length === 0) return false;
    const linkTextLength = Array.from(links).reduce((sum, a) => sum + a.textContent.trim().length, 0);
    const totalTextLength = element.textContent.trim().length;
    // If >80% of text is inside links, it's likely a navigation item
    return totalTextLength > 0 && (linkTextLength / totalTextLength) > 0.8;
}

// Split long text into sentence-based chunks for BERT processing
function splitIntoChunks(text, maxLength = 1500) {
    if (text.length <= maxLength) return [text];

    const chunks = [];
    // Split on sentence boundaries (period/question/exclamation followed by space or end)
    const sentences = text.match(/[^.!?]*[.!?]+[\s]*/g) || [text];
    let currentChunk = '';

    for (const sentence of sentences) {
        if (currentChunk.length + sentence.length > maxLength && currentChunk.length > 0) {
            chunks.push(currentChunk.trim());
            currentChunk = sentence;
        } else {
            currentChunk += sentence;
        }
    }
    if (currentChunk.trim().length > 50) {
        chunks.push(currentChunk.trim());
    }

    return chunks.length > 0 ? chunks : [text.substring(0, maxLength)];
}

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
    
    // Expanded selectors to capture more clause structures
    const paragraphs = contentElement.querySelectorAll('p, li, dd, blockquote, td, div.clause, div.section, section > div, article > div');
    const clauses = [];
    const seenTexts = new Set(); // Track seen text to avoid duplicates
    
    paragraphs.forEach(p => {
        // Skip elements in navigation/TOC/sidebar containers
        if (isInExcludedContainer(p)) return;

        // Skip list items that are primarily navigation links
        if (isNavLink(p)) return;

        // Privacy: skip form elements and user-specific content areas
        if (isUserContentArea(p)) return;

        const text = p.textContent.trim();

        // Filter: minimum 50 chars, maximum 5000 chars (raised to capture long legal clauses)
        if (text.length < 50 || text.length > 5000) return;

        // Substring-based deduplication: skip if this text is contained in or contains an existing entry
        let isDuplicate = false;
        for (const seen of seenTexts) {
            if (seen === text || seen.includes(text) || text.includes(seen)) {
                isDuplicate = true;
                break;
            }
        }
        if (isDuplicate) return;

        seenTexts.add(text);

        // Split long clauses into BERT-friendly chunks while keeping element reference
        // Privacy: redact any PII before storing text for API transmission
        if (text.length > 1500) {
            const chunks = splitIntoChunks(text);
            for (const chunk of chunks) {
                clauses.push({
                    text: redactPII(chunk),
                    element: p
                });
            }
        } else {
            clauses.push({
                text: redactPII(text),
                element: p
            });
        }
    });
    
    // Don't limit clauses - we'll process them progressively
    console.log(`Extracted ${clauses.length} potential clauses (filtered ${paragraphs.length - clauses.length} duplicates/invalid)`);
    return clauses;
}

// Send clauses to API for classification (routed through background.js queue)
async function classifyClauses(clauses) {
    // Security: verify API URL is local-only before sending any data
    if (!isApiUrlSafe(API_URL)) {
        console.error('Security: API URL is not a local address. Blocking data transmission.');
        showError('Security error: Data can only be sent to a local API server.');
        return null;
    }

    try {
        const clauseTexts = clauses.map(c => c.text);

        // Process in chunks to show progress and avoid large payloads
        const CHUNK_SIZE = 15;
        const results = [];

        if (clauseTexts.length > CHUNK_SIZE) {
            console.log(`Processing ${clauseTexts.length} clauses in chunks of ${CHUNK_SIZE}...`);

            for (let i = 0; i < clauseTexts.length; i += CHUNK_SIZE) {
                const chunk = clauseTexts.slice(i, i + CHUNK_SIZE);
                console.log(`Processing chunk ${Math.floor(i/CHUNK_SIZE) + 1}/${Math.ceil(clauseTexts.length/CHUNK_SIZE)}...`);

                // Update loading message
                updateLoadingMessage(`Analyzing clauses ${i + 1}-${Math.min(i + CHUNK_SIZE, clauseTexts.length)} of ${clauseTexts.length}...`);

                const chunkResults = await sendToQueue(chunk);
                if (!chunkResults) {
                    throw new Error('Classification failed for chunk');
                }
                results.push(...chunkResults);
            }

            return results;
        } else {
            // Small batch, process all at once
            const batchResults = await sendToQueue(clauseTexts);
            if (!batchResults) {
                throw new Error('Classification failed');
            }
            return batchResults;
        }

    } catch (error) {
        console.error('Classification error:', error);
        if (error.message.includes('Failed to fetch') || error.message.includes('Cannot connect')) {
            showError('Cannot connect to API. Make sure the server is running at localhost:8000');
        } else {
            showError('Classification failed: ' + error.message);
        }
        return null;
    }
}

// Send a batch of clauses to the background.js batch aggregator
function sendToQueue(clauseTexts) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
            { action: 'classifyBatch', apiUrl: API_URL, clauses: clauseTexts },
            (response) => {
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                    return;
                }
                if (response && response.success) {
                    resolve(response.results);
                } else {
                    reject(new Error(response ? response.error : 'No response from background'));
                }
            }
        );
    });
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
    
    // Send to background script (privacy: only store metadata, not raw clause text)
    chrome.runtime.sendMessage({
        action: 'updateResults',
        results: sanitizeResultsForStorage(analysisResults)
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
    classification.risks_detected.forEach((risk, riskIndex) => {
        html += `<div class="risk-detail">`;
        html += `  <h4>${risk.risk_type}</h4>`;
        html += `  <p>Confidence: ${(risk.confidence * 100).toFixed(1)}%</p>`;
        
        // On-demand explanation accordion
        html += `  <div class="llm-explanation-accordion" id="ext-explain-${riskIndex}">`;
        html += `    <button class="ext-accordion-btn" id="ext-btn-${riskIndex}" 
                         data-clause="${encodeURIComponent(classification.clause || '')}" 
                         data-risk-type="${risk.risk_type}" 
                         data-index="${riskIndex}"
                         style="display:flex;align-items:center;padding:8px 0;background:transparent;border:none;color:#667eea;font-weight:600;cursor:pointer;width:100%;text-align:left;font-size:14px;">
                        <span class="ext-accordion-icon" style="margin-right:8px;font-size:12px;">▶</span> 💡 What This Means
                     </button>`;
        html += `    <div class="ext-accordion-content" id="ext-content-${riskIndex}" style="display: none; padding-left: 20px; margin-top: 4px;">`;
        if (risk.explanation) {
            html += `      <p class="ext-explanation-text" id="ext-text-${riskIndex}" style="margin:0;font-size:13px;line-height:1.4;color:#dde2eb;">${risk.explanation}</p>`;
        } else {
            html += `      <p class="ext-explanation-text" id="ext-text-${riskIndex}" style="margin:0;font-size:13px;line-height:1.4;color:#dde2eb;"></p>`;
        }
        html += `    </div>`;
        html += `  </div>`;
        
        html += `</div>`;
    });
    html += '</div>';
    
    // Attention Visualization
    if (classification.attention_explanation) {
        const attention = classification.attention_explanation;
        
        html += '<div class="attention-section">';
        html += '<h3>🔍 Why This Was Detected</h3>';
        
        // Heatmap visualization
        html += '<div class="attention-heatmap">';
        html += '<p class="heatmap-label">Word Importance Heatmap:</p>';
        html += '<div class="heatmap-text">';
        
        attention.heatmap_data.forEach(item => {
            const intensity = item.normalized;
            const style = getHeatmapStyle(intensity);
            
            html += `
                <span class="heatmap-word" 
                      style="background-color: ${style.bg}; color: ${style.fg}; font-weight: ${style.weight}; font-size: ${style.size}; margin: 3px 2px;"
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
    
    // Add click handlers for accordion buttons
    modal.querySelectorAll('.ext-accordion-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const riskIndex = this.dataset.index;
            const clause = decodeURIComponent(this.dataset.clause);
            const riskType = this.dataset.riskType;
            const contentDiv = document.getElementById(`ext-content-${riskIndex}`);
            const textEl = document.getElementById(`ext-text-${riskIndex}`);
            const iconEl = this.querySelector('.ext-accordion-icon');
            
            // Toggle accordion visibility
            if (contentDiv.style.display === 'block') {
                contentDiv.style.display = 'none';
                iconEl.textContent = '▶';
                return;
            } else {
                contentDiv.style.display = 'block';
                iconEl.textContent = '▼';
            }
            
            // If we already have text or are already fetching, don't fetch again
            if (contentDiv.dataset.fetched) {
                return;
            }
            
            contentDiv.dataset.fetched = 'loading';
            textEl.innerHTML = '<span class="explanation-loading">Generating explanation<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span></span>';
            
            // Stream explanation (privacy: redact PII from clause before sending)
            try {
                const sanitizedClause = redactPII(clause);
                const response = await fetch(`${API_URL}/explain`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ clause: sanitizedClause, risk_type: riskType }),
                    signal: AbortSignal.timeout(60000)
                });
                
                const contentType = response.headers.get('content-type') || '';
                
                if (contentType.includes('text/event-stream')) {
                    textEl.textContent = '';
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop();
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    if (data.token) {
                                        textEl.textContent += data.token;
                                    }
                                    if (data.done) break;
                                } catch (e) { }
                            }
                        }
                    }
                } else {
                    const data = await response.json();
                    textEl.textContent = data.explanation;
                }
                
                contentDiv.dataset.fetched = 'done';
            } catch (error) {
                console.error('Extension explanation error:', error);
                textEl.textContent = 'Failed to generate explanation. Check if server is running.';
                delete contentDiv.dataset.fetched;
            }
        });
    });
    
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

// Helper function for heatmap colors (tuned for dark extension modal)
function getHeatmapStyle(intensity) {
    if (intensity < 0.15) {
        return { bg: 'transparent', fg: '#ccc', weight: 'normal', size: '14px' };
    } else if (intensity < 0.35) {
        return { bg: '#fff9c4', fg: '#333', weight: 'normal', size: '14px' }; // Light Yellow
    } else if (intensity < 0.6) {
        return { bg: '#ffe082', fg: '#856404', weight: '500', size: '15px' }; // Amber
    } else if (intensity < 0.8) {
        return { bg: '#ffb74d', fg: '#541f00', weight: '600', size: '16px' }; // Orange
    } else if (intensity < 0.95) {
        return { bg: '#f4511e', fg: '#fff', weight: '700', size: '17px' };  // Deep Orange
    } else {
        return { bg: '#d32f2f', fg: '#fff', weight: 'bold', size: '18px' };  // Red
    }
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
async function analyzeToS(skipLegalCheck = false) {
    console.log('Starting ToS analysis...');

    // Privacy: verify this page is actually a legal document before extracting content
    // Skip this check when the user manually triggers analysis from the popup
    if (!skipLegalCheck && !isLikelyLegalPage()) {
        console.log('Page does not appear to be a legal document. Skipping analysis to protect privacy.');
        return;
    }
    
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
    
    // Split into initial batch (10) and remaining
    const INITIAL_BATCH_SIZE = 10;
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

// Auto-run analysis only on pages whose URL path (not query string) suggests legal content
const urlPath = window.location.pathname.toLowerCase();
const isLegalPath = /(terms|tos|service|privacy|legal|policy|agreement)/i.test(urlPath);
if (isLegalPath) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', analyzeToS);
    } else {
        analyzeToS();
    }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'ping') {
        sendResponse({ alive: true });
    } else if (request.action === 'getResults') {
        sendResponse(analysisResults);
    } else if (request.action === 'reanalyze') {
        analyzeToS(true);
        sendResponse({ success: true });
    } else if (request.action === 'queueUpdate') {
        // Background.js is telling us our queue position
        const loader = document.getElementById('tos-loader');
        if (loader && request.position > 0) {
            updateLoadingMessage(`Waiting in queue (position ${request.position} of ${request.totalQueued})...`);
        }
    }
});
