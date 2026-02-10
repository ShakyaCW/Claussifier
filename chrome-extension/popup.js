// Popup script
console.log('ToS Risk Detector: Popup loaded');

// Load and display results
async function loadResults() {
    try {
        // Get current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Get results from storage
        const result = await chrome.storage.local.get([`results_${tab.id}`]);
        const results = result[`results_${tab.id}`];
        
        if (!results) {
            showNoData();
            return;
        }
        
        displayResults(results);
        
    } catch (error) {
        console.error('Error loading results:', error);
        showNoData();
    }
}

// Display results in popup
function displayResults(results) {
    const content = document.getElementById('content');
    
    // Determine overall risk level
    let riskLevel = 'Low';
    let riskBadge = '🟢';
    
    if (results.highRisk > 0) {
        riskLevel = 'High';
        riskBadge = '🔴';
    } else if (results.mediumRisk > 0) {
        riskLevel = 'Medium';
        riskBadge = '🟡';
    }
    
    // Count risk types
    const riskTypeCounts = {};
    results.classifications.forEach(classification => {
        if (classification.is_risky) {
            classification.risks_detected.forEach(risk => {
                riskTypeCounts[risk.risk_type] = (riskTypeCounts[risk.risk_type] || 0) + 1;
            });
        }
    });
    
    // Get safe categories (categories that appear in safe_categories across all clauses)
    const safeCategorySet = new Set();
    results.classifications.forEach(classification => {
        classification.safe_categories.forEach(cat => {
            safeCategorySet.add(cat);
        });
    });
    
    // Build HTML
    let html = `
        <div class="risk-summary">
            <div class="risk-level">
                <h2>Overall Risk: ${riskLevel}</h2>
                <div class="risk-badge">${riskBadge}</div>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card high">
                <div class="stat-number">${results.highRisk}</div>
                <div class="stat-label">High Risk</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-number">${results.mediumRisk}</div>
                <div class="stat-label">Medium Risk</div>
            </div>
            <div class="stat-card low">
                <div class="stat-number">${results.lowRisk}</div>
                <div class="stat-label">Safe</div>
            </div>
        </div>
    `;
    
    // Risk types found
    if (Object.keys(riskTypeCounts).length > 0) {
        html += '<div class="risk-list">';
        html += '<h3>⚠️ Risks Found (' + Object.keys(riskTypeCounts).length + ')</h3>';
        
        Object.entries(riskTypeCounts)
            .sort((a, b) => b[1] - a[1])
            .forEach(([riskType, count]) => {
                html += `
                    <div class="risk-item">
                        <span class="risk-name">${riskType}</span>
                        <span class="risk-count">${count}</span>
                    </div>
                `;
            });
        
        html += '</div>';
    }
    
    // Safe categories
    if (safeCategorySet.size > 0) {
        html += '<div class="safe-list">';
        html += '<h3>✓ Safe Categories (' + safeCategorySet.size + ')</h3>';
        
        Array.from(safeCategorySet)
            .sort()
            .forEach(category => {
                html += `<div class="safe-item">${category}</div>`;
            });
        
        html += '</div>';
    }
    
    // Actions
    html += `
        <div class="actions">
            <button class="btn btn-secondary" id="reanalyze">Reanalyze</button>
            <button class="btn btn-primary" id="export">Export Report</button>
        </div>
    `;
    
    content.innerHTML = html;
    
    // Add event listeners
    document.getElementById('reanalyze').addEventListener('click', reanalyze);
    document.getElementById('export').addEventListener('click', () => exportReport(results));
}

// Show no data message
function showNoData() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="no-data">
            <p>📄 No Terms of Service detected on this page.</p>
            <p style="font-size: 12px; color: #666;">
                Navigate to a Terms of Service page to see risk analysis.
            </p>
            <button class="btn btn-primary" id="manualAnalyze" style="margin-top: 15px;">
                Analyze This Page
            </button>
        </div>
    `;
    
    document.getElementById('manualAnalyze').addEventListener('click', reanalyze);
}

// Reanalyze current page
async function reanalyze() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Analyzing page...</p>
        </div>
    `;
    
    // Send message to content script
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.tabs.sendMessage(tab.id, { action: 'reanalyze' }, (response) => {
        setTimeout(loadResults, 2000); // Wait for analysis to complete
    });
}

// Export report
function exportReport(results) {
    // Create text report
    let report = 'ToS Risk Analysis Report\n';
    report += '='.repeat(50) + '\n\n';
    
    report += `Overall Risk Level: ${results.highRisk > 0 ? 'HIGH' : results.mediumRisk > 0 ? 'MEDIUM' : 'LOW'}\n`;
    report += `Total Clauses Analyzed: ${results.total}\n`;
    report += `High Risk Clauses: ${results.highRisk}\n`;
    report += `Medium Risk Clauses: ${results.mediumRisk}\n`;
    report += `Safe Clauses: ${results.lowRisk}\n\n`;
    
    report += 'Detailed Findings:\n';
    report += '-'.repeat(50) + '\n\n';
    
    results.classifications.forEach((classification, index) => {
        if (classification.is_risky) {
            report += `Clause ${index + 1}:\n`;
            classification.risks_detected.forEach(risk => {
                report += `  - ${risk.risk_type} (${(risk.confidence * 100).toFixed(1)}% confidence)\n`;
            });
            report += '\n';
        }
    });
    
    // Download as text file
    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tos-risk-report.txt';
    a.click();
    URL.revokeObjectURL(url);
}

// About link
document.getElementById('about').addEventListener('click', (e) => {
    e.preventDefault();
    alert('ToS Risk Detector v1.0\n\nPowered by Legal-BERT\nTrained on 9,000+ Terms of Service clauses\n76% F1 Score\n\nDetects 8 types of risky clauses:\n- Limitation of liability\n- Unilateral termination\n- Unilateral change\n- Content removal\n- Contract by using\n- Choice of law\n- Jurisdiction\n- Arbitration');
});

// Load results on popup open
loadResults();
