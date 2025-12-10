/**
 * INACTIVITY TIMEOUT MONITOR
 * ✅ Logs out user after 5 minutes (300 seconds) of inactivity
 * ✅ Tracks: mouse movement, keyboard, clicks, scrolls, form input
 * ✅ Works on ANY page the user is on
 * ✅ Shows warning 1 minute before logout
 * ✅ More robust with improved error handling and state management
 */

// ✅ Prevent duplicate class declaration when script loads multiple times
if (typeof InactivityMonitor === 'undefined') {
class InactivityMonitor {
    constructor(options = {}) {
        // ✅ Configuration (changed to 5 minutes with 1 minute warning)
        this.inactivityTimeoutMs = options.inactivityTimeoutMs || 300000; // 300 seconds (5 minutes)
        this.warningTimeMs = options.warningTimeMs || 240000; // Show warning at 240 seconds (1 minute before logout)
        this.logoutUrl = options.logoutUrl || '/logout';
        this.activityDebounceMs = options.activityDebounceMs || 1000; // Debounce activity detection (1 second)

        // ✅ State
        this.inactivityTimer = null;
        this.warningTimer = null;
        this.countdownInterval = null;
        this.isMonitoring = false;
        this.lastActivityTime = new Date();
        this.warningShown = false;
        this.logoutInProgress = false;

        // ✅ Activity event listeners
        this.activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click', 'input', 'change', 'focus'];

        // ✅ Bind handlers to preserve 'this' context
        this.boundActivityHandler = this.onUserActivity.bind(this);
    }

    start() {
        if (this.isMonitoring) {
            console.log('[INACTIVITY MONITOR] ℹ️ Already monitoring inactivity');
            return;
        }

        console.log('[INACTIVITY MONITOR] ✅ Starting inactivity monitor (timeout: 5 minutes, warning: 1 minute)');
        this.isMonitoring = true;
        this.logoutInProgress = false;
        this.attachActivityListeners();
        this.resetInactivityTimer();
    }

    stop() {
        console.log('[INACTIVITY MONITOR] ⏹️ Stopping inactivity monitor');
        this.isMonitoring = false;
        this.detachActivityListeners();
        this.clearTimers();
    }

    /**
     * Attach listeners to detect user activity
     */
    attachActivityListeners() {
        try {
            this.activityEvents.forEach(event => {
                document.addEventListener(event, this.boundActivityHandler, true);
            });
            console.log('[INACTIVITY MONITOR] ✅ Activity listeners attached (' + this.activityEvents.length + ' events)');
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error attaching activity listeners:', e);
        }
    }

    /**
     * Remove activity listeners (cleanup)
     */
    detachActivityListeners() {
        try {
            this.activityEvents.forEach(event => {
                document.removeEventListener(event, this.boundActivityHandler, true);
            });
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error detaching activity listeners:', e);
        }
    }

    /**
     * Called whenever user performs activity
     */
    onUserActivity() {
        // Don't process if not monitoring or logout in progress
        if (!this.isMonitoring || this.logoutInProgress) {
            return;
        }

        const now = new Date();
        const timeSinceLastActivity = now - this.lastActivityTime;

        // ✅ Only reset if activity happened > debounce time ago (prevent rapid-fire resets)
        if (timeSinceLastActivity > this.activityDebounceMs) {
            this.lastActivityTime = now;
            console.log('[INACTIVITY MONITOR] 🎯 User activity detected - resetting timeout');

            // Clear existing timers
            this.clearTimers();

            // Hide warning if showing
            this.hideWarningDialog();
            this.warningShown = false;

            // Reset timers
            this.resetInactivityTimer();
        }
    }

    /**
     * Clear all timers safely
     */
    clearTimers() {
        try {
            if (this.inactivityTimer) {
                clearTimeout(this.inactivityTimer);
                this.inactivityTimer = null;
            }
            if (this.warningTimer) {
                clearTimeout(this.warningTimer);
                this.warningTimer = null;
            }
            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
                this.countdownInterval = null;
            }
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error clearing timers:', e);
        }
    }

    /**
     * Reset the inactivity timer
     */
    resetInactivityTimer() {
        try {
            this.clearTimers();

            // ✅ Set warning timer (1 minute before logout)
            this.warningTimer = setTimeout(() => {
                if (!this.warningShown && this.isMonitoring) {
                    this.showWarningDialog();
                    this.warningShown = true;
                }
            }, this.warningTimeMs);

            // ✅ Set logout timer (5 minutes)
            this.inactivityTimer = setTimeout(() => {
                if (this.isMonitoring && !this.logoutInProgress) {
                    this.handleInactivityLogout();
                }
            }, this.inactivityTimeoutMs);

            console.log(`[INACTIVITY MONITOR] ⏱️ Inactivity timer reset (logout in ${this.inactivityTimeoutMs / 1000}s, warning in ${this.warningTimeMs / 1000}s)`);
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error resetting inactivity timer:', e);
        }
    }

    /**
     * Show warning dialog before logout
     */
    showWarningDialog() {
        try {
            console.warn('[INACTIVITY MONITOR] ⚠️ WARNING: User will be logged out in 1 minute due to inactivity');

            // Create warning alert at top of page
            let warningAlert = document.getElementById('inactivityWarning');
            if (!warningAlert) {
                warningAlert = document.createElement('div');
                warningAlert.id = 'inactivityWarning';
                warningAlert.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                    color: white;
                    padding: 20px;
                    box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
                    z-index: 10000;
                    animation: slideDown 0.4s ease;
                    border-bottom: 3px solid #9a2128;
                `;

                warningAlert.innerHTML = `
                    <div style="
                        max-width: 1200px;
                        margin: 0 auto;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        gap: 20px;
                        flex-wrap: wrap;
                    ">
                        <div style="display: flex; align-items: center; gap: 15px; flex: 1; min-width: 300px;">
                            <span style="font-size: 32px; font-weight: bold;">⏰</span>
                            <div>
                                <h4 style="margin: 0; font-size: 18px; font-weight: bold;">Session Expiring Soon!</h4>
                                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.95;">
                                    You will be logged out in <span id="countdownTimer" style="font-weight: bold; font-size: 18px; color: #ffeb3b;">60</span> seconds due to inactivity.
                                </p>
                            </div>
                        </div>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <button id="stayLoggedInBtn" style="
                                background: linear-gradient(135deg, #28a745 0%, #218838 100%);
                                color: white;
                                border: none;
                                padding: 12px 24px;
                                border-radius: 4px;
                                cursor: pointer;
                                font-weight: bold;
                                font-size: 14px;
                                transition: all 0.3s ease;
                                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                            " onmouseover="this.style.background='linear-gradient(135deg, #218838 0%, #1e7e34 100%)'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0, 0, 0, 0.3)';"
                               onmouseout="this.style.background='linear-gradient(135deg, #28a745 0%, #218838 100%)'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0, 0, 0, 0.2)';">
                                ✓ Stay Logged In
                            </button>
                        </div>
                    </div>
                `;

                document.body.insertBefore(warningAlert, document.body.firstChild);

                // Add CSS animations if not already added
                if (!document.getElementById('inactivityStyles')) {
                    const style = document.createElement('style');
                    style.id = 'inactivityStyles';
                    style.textContent = `
                        @keyframes slideDown {
                            from {
                                opacity: 0;
                                transform: translateY(-100%);
                            }
                            to {
                                opacity: 1;
                                transform: translateY(0);
                            }
                        }
                        
                        @keyframes pulse {
                            0%, 100% {
                                opacity: 1;
                                transform: scale(1);
                            }
                            50% {
                                opacity: 0.7;
                                transform: scale(1.1);
                            }
                        }
                    `;
                    document.head.appendChild(style);
                }

                // "Stay Logged In" button handler
                try {
                    document.getElementById('stayLoggedInBtn').addEventListener('click', () => {
                        console.log('[INACTIVITY MONITOR] User clicked "Stay Logged In"');
                        this.onUserActivity();
                    });
                } catch (e) {
                    console.error('[INACTIVITY MONITOR] ❌ Error attaching stay logged in button handler:', e);
                }
            } else {
                warningAlert.style.display = 'block';
            }

            // ✅ Start countdown timer (60 seconds)
            let countdown = 60;
            const countdownEl = document.getElementById('countdownTimer');

            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
            }

            this.countdownInterval = setInterval(() => {
                countdown--;
                if (countdownEl) {
                    countdownEl.textContent = countdown;
                    // Make it pulse/flash in last 10 seconds
                    if (countdown <= 10) {
                        countdownEl.style.animation = 'pulse 0.5s ease infinite';
                    }
                }

                if (countdown <= 0) {
                    if (this.countdownInterval) {
                        clearInterval(this.countdownInterval);
                        this.countdownInterval = null;
                    }
                }
            }, 1000);
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error showing warning dialog:', e);
        }
    }

    /**
     * Hide warning dialog
     */
    hideWarningDialog() {
        try {
            const warningModal = document.getElementById('inactivityWarning');
            if (warningModal) {
                warningModal.style.display = 'none';
            }
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error hiding warning dialog:', e);
        }
    }

    /**
     * Handle inactivity logout
     */
    handleInactivityLogout() {
        // Prevent multiple logout attempts
        if (this.logoutInProgress) {
            return;
        }

        this.logoutInProgress = true;
        console.error('[INACTIVITY MONITOR] ❌ Inactivity timeout reached - LOGGING OUT USER');

        this.stop();

        try {
            // Show logout message
            const message = 'Your session has expired due to inactivity. You have been logged out.';
            console.error('[INACTIVITY MONITOR]', message);

            // Redirect to logout URL
            // The server will handle session cleanup
            window.location.href = this.logoutUrl;
        } catch (e) {
            console.error('[INACTIVITY MONITOR] ❌ Error during logout:', e);
            // Force page reload as fallback
            window.location.reload();
        }
    }

    /**
     * Get remaining time before logout (in seconds)
     */
    getRemainingTimeSeconds() {
        if (!this.inactivityTimer) {
            return 0;
        }
        const timeRemaining = this.lastActivityTime.getTime() + this.inactivityTimeoutMs - new Date().getTime();
        return Math.max(0, Math.ceil(timeRemaining / 1000));
    }

    /**
     * Get status info for debugging
     */
    getStatus() {
        return {
            isMonitoring: this.isMonitoring,
            logoutInProgress: this.logoutInProgress,
            lastActivityTime: this.lastActivityTime,
            remainingSeconds: this.getRemainingTimeSeconds(),
            warningShown: this.warningShown,
            inactivityTimeoutMs: this.inactivityTimeoutMs,
            warningTimeMs: this.warningTimeMs,
        };
    }
}

// ✅ AUTO-START INACTIVITY MONITOR FOR ALL AUTHENTICATED USERS
// ✅ Only initialize if not already initialized (handles script loading multiple times)
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Skip if already initialized on this page
        if (window.inactivityMonitor && window.inactivityMonitor instanceof InactivityMonitor) {
            console.log('[INACTIVITY MONITOR] ℹ️ Already initialized, skipping re-initialization');
            return;
        }

        const monitor = new InactivityMonitor({
            inactivityTimeoutMs: 300000, // 300 seconds (5 minutes)
            warningTimeMs: 240000, // Show warning at 240 seconds (1 minute before logout)
            logoutUrl: '/logout',
            activityDebounceMs: 1000,
        });

        monitor.start();

        // Store globally for debugging
        window.inactivityMonitor = monitor;

        console.log('[INACTIVITY MONITOR] ✅ Inactivity monitor initialized');
        console.log('[INACTIVITY MONITOR] ℹ️ Timeout: 5 minutes | Warning: 1 minute before logout');
    } catch (e) {
        console.error('[INACTIVITY MONITOR] ❌ Error initializing inactivity monitor:', e);
    }
});
} // End of: if (typeof InactivityMonitor === 'undefined')
