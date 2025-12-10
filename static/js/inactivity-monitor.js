/**
 * INACTIVITY TIMEOUT MONITOR
 * ✅ Logs out user after 1 minute (60 seconds) of inactivity
 * ✅ Tracks: mouse movement, keyboard, clicks, scrolls, form input
 * ✅ Works on ANY page the user is on
 * ✅ Shows warning before logout (optional)
 */

class InactivityMonitor {
    constructor(options = {}) {
        // ✅ Configuration
        this.inactivityTimeoutMs = options.inactivityTimeoutMs || 60000; // 60 seconds (1 minute)
        this.warningTimeMs = options.warningTimeMs || 50000; // Show warning at 50 seconds (10 seconds before logout)
        this.logoutUrl = options.logoutUrl || '/logout';

        // ✅ State
        this.inactivityTimer = null;
        this.warningTimer = null;
        this.isMonitoring = false;
        this.lastActivityTime = new Date();
        this.warningShown = false;

        // ✅ Activity event listeners
        this.activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click', 'input'];
    }

    start() {
        if (this.isMonitoring) {
            console.log('[INACTIVITY MONITOR] ℹ️ Already monitoring inactivity');
            return;
        }

        console.log('[INACTIVITY MONITOR] ✅ Starting inactivity monitor (timeout: 60 seconds)');
        this.isMonitoring = true;
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
        this.activityEvents.forEach(event => {
            document.addEventListener(event, () => this.onUserActivity(), true);
        });
        console.log('[INACTIVITY MONITOR] ✅ Activity listeners attached');
    }

    /**
     * Remove activity listeners (cleanup)
     */
    detachActivityListeners() {
        this.activityEvents.forEach(event => {
            document.removeEventListener(event, () => this.onUserActivity(), true);
        });
    }

    /**
     * Called whenever user performs activity
     */
    onUserActivity() {
        // Only reset if actually idle
        if (!this.isMonitoring) {
            return;
        }

        const now = new Date();
        const timeSinceLastActivity = now - this.lastActivityTime;

        // ✅ Only reset if activity happened > 1 second ago (prevent rapid-fire resets)
        if (timeSinceLastActivity > 1000) {
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
     * Clear all timers
     */
    clearTimers() {
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
            this.inactivityTimer = null;
        }
        if (this.warningTimer) {
            clearTimeout(this.warningTimer);
            this.warningTimer = null;
        }
    }

    /**
     * Reset the inactivity timer
     */
    resetInactivityTimer() {
        this.clearTimers();

        // ✅ Set warning timer (10 seconds before logout)
        this.warningTimer = setTimeout(() => {
            if (!this.warningShown) {
                this.showWarningDialog();
                this.warningShown = true;
            }
        }, this.warningTimeMs);

        // ✅ Set logout timer (60 seconds)
        this.inactivityTimer = setTimeout(() => {
            this.handleInactivityLogout();
        }, this.inactivityTimeoutMs);

        console.log(`[INACTIVITY MONITOR] ⏱️ Inactivity timer reset (logout in ${this.inactivityTimeoutMs}ms)`);
    }

    /**
     * Show warning dialog before logout
     */
    showWarningDialog() {
        console.warn('[INACTIVITY MONITOR] ⚠️ WARNING: User will be logged out in 10 seconds due to inactivity');

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
                background: linear-gradient(135deg, #28a745 0%, #218838 100%);
                color: white;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
                z-index: 10000;
                animation: slideDown 0.4s ease;
                border-bottom: 3px solid #1e7e34;
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
                        <span style="font-size: 32px; font-weight: bold;">✓</span>
                        <div>
                            <h4 style="margin: 0; font-size: 18px; font-weight: bold;">Session Expiring!</h4>
                            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.95;">
                                You will be logged out in <span id="countdownTimer" style="font-weight: bold; font-size: 16px;">10</span> seconds due to inactivity.
                            </p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button id="stayLoggedInBtn" style="
                            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 4px;
                            cursor: pointer;
                            font-weight: bold;
                            font-size: 14px;
                            transition: all 0.3s ease;
                            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                        " onmouseover="this.style.background='linear-gradient(135deg, #bd2130 0%, #a71d2a 100%)'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0, 0, 0, 0.3)';"
                           onmouseout="this.style.background='linear-gradient(135deg, #dc3545 0%, #c82333 100%)'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0, 0, 0, 0.2)';">
                            Stay Logged In
                        </button>
                    </div>
                </div>
            `;

            document.body.insertBefore(warningAlert, document.body.firstChild);

            // Add CSS animations
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
                        }
                        50% {
                            opacity: 0.7;
                        }
                    }
                `;
                document.head.appendChild(style);
            }

            // "Stay Logged In" button handler
            document.getElementById('stayLoggedInBtn').addEventListener('click', () => {
                this.onUserActivity(); // Reset timeout as if user was active
            });
        } else {
            warningAlert.style.display = 'block';
        }

        // ✅ Start countdown timer (10 seconds)
        let countdown = 10;
        const countdownInterval = setInterval(() => {
            countdown--;
            const countdownEl = document.getElementById('countdownTimer');
            if (countdownEl) {
                countdownEl.textContent = countdown;
                // Make it pulse/flash in last 3 seconds
                if (countdown <= 3) {
                    countdownEl.style.animation = 'pulse 0.5s ease infinite';
                }
            }

            if (countdown <= 0) {
                clearInterval(countdownInterval);
            }
        }, 1000);
    }

    /**
     * Hide warning dialog
     */
    hideWarningDialog() {
        const warningModal = document.getElementById('inactivityWarning');
        if (warningModal) {
            warningModal.style.display = 'none';
        }
    }

    /**
     * Handle inactivity logout
     */
    handleInactivityLogout() {
        console.error('[INACTIVITY MONITOR] ❌ Inactivity timeout reached - LOGGING OUT USER');

        this.stop();

        // Show logout message
        const message = 'Your session has expired due to inactivity. You have been logged out.';
        console.error('[INACTIVITY MONITOR]', message);

        // Redirect to logout URL
        // The server will handle session cleanup
        window.location.href = this.logoutUrl;
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
            lastActivityTime: this.lastActivityTime,
            remainingSeconds: this.getRemainingTimeSeconds(),
            warningShown: this.warningShown,
            inactivityTimeoutMs: this.inactivityTimeoutMs,
        };
    }
}

// ✅ AUTO-START INACTIVITY MONITOR FOR ALL AUTHENTICATED USERS
document.addEventListener('DOMContentLoaded', function() {
    // Start inactivity monitor for any authenticated user
    // (not just admins - this should work for all roles)

    const monitor = new InactivityMonitor({
        inactivityTimeoutMs: 60000, // 60 seconds (1 minute)
        warningTimeMs: 50000, // Show warning at 50 seconds
        logoutUrl: '/logout',
    });

    monitor.start();

    // Store globally for debugging
    window.inactivityMonitor = monitor;

    console.log('[INACTIVITY MONITOR] ✅ Inactivity monitor initialized');
    console.log('[INACTIVITY MONITOR] ℹ️ Timeout: 60 seconds | Warning: at 50 seconds');
});
