// Background service worker
console.log('ToS Risk Detector: Background script loaded');

let currentResults = null;

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
    }
});

// Clear badge when tab is updated
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'loading') {
        chrome.action.setBadgeText({ text: '', tabId: tabId });
    }
});
