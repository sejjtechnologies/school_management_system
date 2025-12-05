/**
 * Admin Session Monitor
 * Polls /api/check-session every 3 seconds to detect if session is still valid
 * Auto-logs out if another device logs in with same credentials
 */

class AdminSessionMonitor {
    constructor(options = {}) {
        this.checkIntervalMs = options.checkIntervalMs || 3000; // Check every 3 seconds
        this.checkUrl = options.checkUrl || '/api/check-session';
        this.isMonitoring = false;
        this.lastCheckTime = null;
        this.failureCount = 0;
        this.maxFailures = 3; // Allow 3 failures before alerting
    }

    start() {
        if (this.isMonitoring) {
            console.log('[SESSION MONITOR] Already monitoring');
            return;
        }

        console.log('[SESSION MONITOR] Starting session validation polling...');
        this.isMonitoring = true;
        this.pollSessionValidity();
    }

    stop() {
        console.log('[SESSION MONITOR] Stopping session validation polling');
        this.isMonitoring = false;
    }

    async pollSessionValidity() {
        while (this.isMonitoring) {
            try {
                this.lastCheckTime = new Date();
                const response = await fetch(this.checkUrl, {
                    method: 'GET',
                    credentials: 'include', // Include cookies
                    headers: {
                        'Accept': 'application/json',
                    }
                });

                if (!response.ok) {
                    const data = await response.json();
                    console.warn('[SESSION MONITOR] Session invalid:', data.message);
                    
                    // Show logout message and redirect
                    this.handleSessionInvalid(data);
                    return; // Stop monitoring
                } else {
                    const data = await response.json();
                    if (!data.valid) {
                        console.warn('[SESSION MONITOR] Session marked invalid:', data.message);
                        this.handleSessionInvalid(data);
                        return; // Stop monitoring
                    }

                    // Session is still valid
                    this.failureCount = 0;
                    console.log('[SESSION MONITOR] Session valid at', this.lastCheckTime.toLocaleTimeString());
                }
            } catch (error) {
                this.failureCount++;
                console.error('[SESSION MONITOR] Check failed:', error.message);
                
                // If we get too many failures, something is wrong
                if (this.failureCount >= this.maxFailures) {
                    console.error('[SESSION MONITOR] Too many failures, stopping monitor');
                    this.stop();
                    return;
                }
            }

            // Wait before next check
            await new Promise(resolve => setTimeout(resolve, this.checkIntervalMs));
        }
    }

    handleSessionInvalid(data) {
        console.error('[SESSION MONITOR] Session invalid - logging out user');
        this.stop();

        // Get appropriate message
        let message = data.message || 'Your session has been invalidated';
        
        if (data.reason === 'multi_device_login') {
            message = 'You logged in from another device. This session is now closed.';
        } else if (data.reason === 'session_inactive') {
            message = 'You logged in from another device. This session is now closed.';
        }

        // Show alert
        const alertDiv = document.createElement('div');
        alertDiv.id = 'session-invalid-alert';
        alertDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;

        const card = document.createElement('div');
        card.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            text-align: center;
        `;

        card.innerHTML = `
            <h2 style="color: #dc3545; margin: 0 0 15px 0;">Session Invalidated</h2>
            <p style="color: #666; margin: 0 0 20px 0; font-size: 14px;">
                ${message}
            </p>
            <p style="color: #999; margin: 0 0 20px 0; font-size: 12px;">
                Redirecting to login...
            </p>
            <button onclick="location.href='/login'" style="
                background: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            ">Go to Login</button>
        `;

        alertDiv.appendChild(card);
        document.body.appendChild(alertDiv);

        // Redirect to login after 3 seconds
        setTimeout(() => {
            window.location.href = '/login';
        }, 3000);
    }
}

// ✅ Auto-start monitor for admin users
document.addEventListener('DOMContentLoaded', function() {
    // Only start if we're on an admin page
    if (window.location.pathname.includes('/admin') || 
        window.location.pathname.includes('/dashboard')) {
        
        // Check if user is admin
        const userRole = document.body.getAttribute('data-user-role');
        if (userRole && userRole.toLowerCase() === 'admin') {
            const monitor = new AdminSessionMonitor({
                checkIntervalMs: 3000, // Check every 3 seconds
            });
            monitor.start();
            
            // Store globally so it can be stopped if needed
            window.adminSessionMonitor = monitor;
        }
    }
});
