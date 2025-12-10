/**
 * ADMIN SESSION MONITOR - IMMEDIATE CONCURRENT LOGOUT
 * ✅ UPDATED: Polls /api/check-session every 100ms (was 1000ms) for IMMEDIATE detection
 * ✅ FEATURE: Auto-logs out if another device logs in with same admin credentials
 * ✅ BEHAVIOR: INSTANT logout - NO waiting, NO 1 second delay, NO confirmation dialogs
 */

class AdminSessionMonitor {
    constructor(options = {}) {
        // ✅ CRITICAL UPDATE: Changed from 1000ms to 100ms for IMMEDIATE detection
        // This means the old session will detect logout within 100ms of new login
        this.checkIntervalMs = options.checkIntervalMs || 100;
        this.checkUrl = options.checkUrl || '/api/check-session';
        this.isMonitoring = false;
        this.lastCheckTime = null;
        this.failureCount = 0;
        this.maxFailures = 3; // Allow 3 failures before alerting
        this.isHandlingInvalid = false; // ✅ NEW: Guard to prevent duplicate logout handlers
    }

    start() {
        if (this.isMonitoring) {
            console.log('[SESSION MONITOR] ℹ️ Already monitoring session');
            return;
        }

        console.log('[SESSION MONITOR] ✅ Starting session validation (100ms intervals - IMMEDIATE detection)');
        this.isMonitoring = true;
        this.pollSessionValidity();
    }

    stop() {
        console.log('[SESSION MONITOR] ⏹️ Stopping session validation polling');
        this.isMonitoring = false;
    }

    async pollSessionValidity() {
        while (this.isMonitoring) {
            try {
                this.lastCheckTime = new Date();

                // Fetch session status from backend
                const response = await fetch(this.checkUrl, {
                    method: 'GET',
                    credentials: 'include', // Include cookies for session
                    headers: {
                        'Accept': 'application/json',
                    }
                });

                // Handle non-OK response (session invalid)
                if (!response.ok) {
                    const data = await response.json();
                    console.warn('[SESSION MONITOR] ⚠️ Session check returned error:', data.message);

                    // ✅ IMMEDIATE: Call handler WITHOUT any delay
                    if (!this.isHandlingInvalid) {
                        this.handleSessionInvalid(data);
                    }
                    return;
                }

                // Parse JSON response
                const data = await response.json();

                // Check if session marked as invalid
                if (!data.valid) {
                    console.warn('[SESSION MONITOR] ⚠️ Session marked invalid:', data.message);
                    // ✅ IMMEDIATE: Call handler WITHOUT any delay
                    if (!this.isHandlingInvalid) {
                        this.handleSessionInvalid(data);
                    }
                    return;
                }

                // Session still valid - reset failure counter
                this.failureCount = 0;
                // ✅ Suppress verbose logging for every check (100ms = lots of logs)
            }
            catch (error) {
                this.failureCount++;
                console.error('[SESSION MONITOR] ❌ Network error during check:', error.message);

                // Stop monitoring after too many failures
                if (this.failureCount >= this.maxFailures) {
                    console.error('[SESSION MONITOR] ❌ Too many failures - stopping monitor');
                    this.stop();
                    return;
                }
            }

            // ✅ Wait 100ms before next check
            // This ensures old session detects logout within 100ms of new device login
            await new Promise(resolve => setTimeout(resolve, this.checkIntervalMs));
        }
    }

    handleSessionInvalid(data) {
        // ✅ GUARD: Prevent multiple simultaneous redirects
        // If another session check happens at the exact same time, ignore it
        if (this.isHandlingInvalid) {
            console.log('[SESSION MONITOR] ℹ️ Logout already in progress, ignoring duplicate');
            return;
        }
        this.isHandlingInvalid = true;

        // Stop the monitoring loop
        this.stop();

        // Build logout message
        let logoutReason = 'Session invalidated';

        if (data.reason === 'multi_device_login') {
            logoutReason = '🔐 ADMIN LOGGED IN FROM ANOTHER DEVICE - THIS SESSION CLOSED IMMEDIATELY';
        } else if (data.reason === 'session_inactive') {
            logoutReason = '🔐 SESSION INACTIVE (another device login detected) - CLOSED IMMEDIATELY';
        }

        console.error('[SESSION MONITOR] ⚠️ ' + logoutReason);
        console.error('[SESSION MONITOR] Details:', data);

        // ✅ INSTANT REDIRECT
        // NO setTimeout, NO delays, NO confirmation dialogs
        // Just redirect immediately to force logout
        // This is truly INSTANT - old session logs out the moment new device logs in (within 100ms)
        window.location.href = '/login';
    }
}

// ✅ Auto-initialize monitor for admin users on page load
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on admin dashboard/pages
    const isAdminPage = window.location.pathname.includes('/admin') ||
                        window.location.pathname.includes('/dashboard');

    if (!isAdminPage) {
        return;
    }

    // Check if user is admin (look for data attribute on body)
    const userRole = document.body.getAttribute('data-user-role');

    if (userRole && userRole.toLowerCase() === 'admin') {
        // ✅ Create monitor with 100ms polling (IMMEDIATE detection)
        const monitor = new AdminSessionMonitor({
            checkIntervalMs: 100, // Check every 100ms (was 1000ms)
        });

        // Start monitoring
        monitor.start();

        // Store globally for debugging
        window.adminSessionMonitor = monitor;

        console.log('[SESSION MONITOR] ✅ Admin session monitor initialized');
        console.log('[SESSION MONITOR] ℹ️ Polling interval: 100ms (IMMEDIATE concurrent logout)');
    }
});
