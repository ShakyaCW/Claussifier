// Background service worker
console.log('ToS Risk Detector: Background script loaded');

let currentResults = null;

// --- BATCH AGGREGATOR ---
// Combines requests from multiple tabs into a single API call for parallel inference.
// This means 5 tabs analyzing simultaneously takes ~the same time as 1 tab.

const BATCH_WINDOW_MS = 50;  // Wait this long to collect requests before sending
const MAX_BATCH_SIZE = 80;   // Max clauses per API call (keep under API's 100 limit)
let pendingRequests = [];     // { tabId, clauses, resolve, reject, apiUrl }
let batchTimer = null;
let isProcessing = false;

function scheduleBatchFlush() {
    if (batchTimer) return; // Already scheduled
    batchTimer = setTimeout(flushBatch, BATCH_WINDOW_MS);
}

async function flushBatch() {
    batchTimer = null;

    if (pendingRequests.length === 0 || isProcessing) return;

    isProcessing = true;

    // Take all pending requests
    const batch = [];
    const taken = [];
    let totalClauses = 0;

    while (pendingRequests.length > 0 && totalClauses + pendingRequests[0].clauses.length <= MAX_BATCH_SIZE) {
        const req = pendingRequests.shift();
        taken.push(req);
        totalClauses += req.clauses.length;
    }

    // Notify remaining requests of their position
    notifyWaitingTabs();

    // Combine all clauses into one flat array
    const allClauses = [];
    const requestMap = []; // Track which clauses belong to which request
    for (const req of taken) {
        const startIdx = allClauses.length;
        allClauses.push(...req.clauses);
        requestMap.push({ request: req, startIdx, count: req.clauses.length });
    }

    // Notify tabs that processing has started
    for (const req of taken) {
        chrome.tabs.sendMessage(req.tabId, {
            action: 'queueUpdate',
            position: 0,  // 0 = currently processing
            totalQueued: pendingRequests.length
        }).catch(() => {});
    }

    const apiUrl = taken[0].apiUrl; // All requests use the same API

    try {
        console.log(`Batch inference: ${allClauses.length} clauses from ${taken.length} request(s)`);

        const response = await fetch(`${apiUrl}/classify-batch-with-attention`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clauses: allClauses })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        const allResults = data.data ? data.data.results : data.results;

        // Distribute results back to each request
        for (const { request, startIdx, count } of requestMap) {
            const results = allResults.slice(startIdx, startIdx + count);
            request.resolve(results);
        }
    } catch (error) {
        // Reject all requests in this batch
        for (const { request } of requestMap) {
            request.reject(error.message);
        }
    } finally {
        isProcessing = false;
        // Process any requests that arrived while we were busy
        if (pendingRequests.length > 0) {
            scheduleBatchFlush();
        }
    }
}

function notifyWaitingTabs() {
    const notifiedTabs = new Set();
    pendingRequests.forEach((req, idx) => {
        if (!notifiedTabs.has(req.tabId)) {
            notifiedTabs.add(req.tabId);
            chrome.tabs.sendMessage(req.tabId, {
                action: 'queueUpdate',
                position: idx + 1,
                totalQueued: pendingRequests.length
            }).catch(() => {});
        }
    });
}

function enqueueRequest(tabId, apiUrl, clauses) {
    return new Promise((resolve, reject) => {
        pendingRequests.push({ tabId, apiUrl, clauses, resolve, reject });
        scheduleBatchFlush();
    });
}
// --- END BATCH AGGREGATOR ---

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'updateBadge') {
        // Update extension badge
        chrome.action.setBadgeText({
            text: request.text,
            tabId: sender.tab.id
        });
        chrome.action.setBadgeBackgroundColor({
            color: request.color,
            tabId: sender.tab.id
        });
    } else if (request.action === 'updateResults') {
        // Store results
        currentResults = request.results;

        // Store in chrome.storage for popup
        chrome.storage.local.set({
            [`results_${sender.tab.id}`]: request.results
        });
    } else if (request.action === 'classifyBatch') {
        // Route API request through the batch aggregator
        const tabId = sender.tab.id;

        enqueueRequest(tabId, request.apiUrl, request.clauses)
            .then(results => {
                sendResponse({ success: true, results });
            })
            .catch(error => {
                sendResponse({ success: false, error });
            });

        return true; // Keep message channel open for async response
    }
});

// Clear badge when tab is updated
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'loading') {
        chrome.action.setBadgeText({ text: '', tabId: tabId });
        // Cancel any pending requests for this tab (page is navigating away)
        for (let i = pendingRequests.length - 1; i >= 0; i--) {
            if (pendingRequests[i].tabId === tabId) {
                pendingRequests[i].reject('Tab navigated away');
                pendingRequests.splice(i, 1);
            }
        }
    }
});
