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
