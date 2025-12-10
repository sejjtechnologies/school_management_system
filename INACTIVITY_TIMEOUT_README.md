# 1-MINUTE INACTIVITY TIMEOUT FEATURE

## Overview
✅ **Status**: Implemented and Ready for Testing

Users are automatically logged out after **60 seconds (1 minute)** of inactivity and redirected to the login page, regardless of which page they are on.

---

## Features

### 1. **Automatic Inactivity Detection**
- Tracks: mousemove, keydown, scroll, touchstart, click, input
- Countdown: 60 seconds from last activity
- Works on ALL pages (admin, teacher, parent, bursar, secretary, headteacher)

### 2. **Warning Dialog (Optional)**
- Shows at **50 seconds** (10 seconds before logout)
- Displays countdown timer
- "Stay Logged In" button to reset timer
- Auto-hides if user becomes active

### 3. **Logout & Redirect**
- Automatic logout after 60 seconds of no activity
- Redirects to `/login`
- Shows message: "Your session has expired due to inactivity. You have been logged out."

### 4. **Activity Events Tracked**
- Mouse movement (`mousedown`)
- Keyboard input (`keydown`)
- Page scrolling (`scroll`)
- Touch events (`touchstart`)
- Clicks (`click`)
- Form input (`input`)

---

## Technical Details

### File Structure
```
static/js/inactivity-monitor.js    # New inactivity monitor class
templates/footer.html               # Modified to include script tag
```

### Implementation
1. Created `InactivityMonitor` class in `static/js/inactivity-monitor.js`
2. Added script tag to `templates/footer.html` to load on all pages
3. Auto-initializes on DOMContentLoaded for all authenticated users

### Configuration
```javascript
const monitor = new InactivityMonitor({
    inactivityTimeoutMs: 60000,  // 60 seconds timeout
    warningTimeMs: 50000,         // Show warning at 50 seconds
    logoutUrl: '/logout',         // Redirect URL
});

monitor.start();
```

### Key Methods
| Method | Purpose |
|--------|---------|
| `start()` | Activate inactivity monitoring |
| `stop()` | Deactivate monitoring (cleanup) |
| `onUserActivity()` | Called on user action; resets timer |
| `resetInactivityTimer()` | Set warning timer (50s) + logout timer (60s) |
| `showWarningDialog()` | Display warning modal with countdown |
| `handleInactivityLogout()` | Execute logout and redirect |
| `getRemainingTimeSeconds()` | Get seconds until logout (for debugging) |
| `getStatus()` | Get monitor status object (for debugging) |

---

## Testing Checklist

### Test Case 1: Basic Inactivity Timeout
```
1. Login to system (any role)
2. Stay idle for 60 seconds
3. Expected: Warning dialog shows at 50 seconds
4. Expected: Auto-logout and redirect to /login at 60 seconds
✅ Test on multiple pages (teacher, admin, bursar, etc.)
```

### Test Case 2: Activity Resets Timer
```
1. Login to system
2. Wait 45 seconds (idle)
3. Move mouse / type / click
4. Expected: Timer resets; warning disappears
5. Expected: No logout occurs
✅ Test multiple times to ensure timer reset works
```

### Test Case 3: "Stay Logged In" Button
```
1. Login to system
2. Wait 50 seconds (warning dialog appears)
3. Click "Stay Logged In" button
4. Expected: Warning disappears; timer resets
5. Expected: User remains logged in
```

### Test Case 4: Multiple Tabs
```
1. Open two tabs in same browser
2. Login on Tab 1
3. Tab 1: Wait 60 seconds (stay idle)
4. Expected: Tab 1 logs out after 60 seconds
5. Expected: Tab 2 should ALSO logout (session invalidated on backend)
   - If admin, both tabs should detect concurrent login via session-monitor.js
   - If teacher/parent, backend validates session on next request
```

### Test Case 5: Page Navigation During Timeout
```
1. Login and navigate to different pages
2. Each page loads inactivity-monitor.js fresh
3. Activity tracked across ALL pages
4. Expected: Single 60-second countdown applies to entire session (not per-page)
```

---

## Browser Console Debugging

### Check Monitor Status
```javascript
// In browser console:
window.inactivityMonitor.getStatus()

// Output example:
{
    isMonitoring: true,
    lastActivityTime: Date,
    remainingSeconds: 45,
    warningShown: false,
    inactivityTimeoutMs: 60000
}
```

### Manually Trigger Timeout (Testing)
```javascript
// Immediately logout (for testing):
window.inactivityMonitor.handleInactivityLogout()

// Manually reset timer:
window.inactivityMonitor.onUserActivity()

// Stop monitoring:
window.inactivityMonitor.stop()

// Start monitoring:
window.inactivityMonitor.start()
```

### View Console Logs
All activity is logged to browser console with `[INACTIVITY MONITOR]` prefix:
```
[INACTIVITY MONITOR] ✅ Starting inactivity monitor (timeout: 60 seconds)
[INACTIVITY MONITOR] ✅ Activity listeners attached
[INACTIVITY MONITOR] 🎯 User activity detected - resetting timeout
[INACTIVITY MONITOR] ⏱️ Inactivity timer reset (logout in 60000ms)
[INACTIVITY MONITOR] ⚠️ WARNING: User will be logged out in 10 seconds due to inactivity
```

---

## Integration Notes

### Where It Loads
- **Script Location**: `static/js/inactivity-monitor.js`
- **Included In**: `templates/footer.html` (line 108-109)
- **Runs On**: All pages that include `footer.html`
- **Auto-Initialization**: On `DOMContentLoaded` event

### Session Cleanup
- Calls `/logout` endpoint which:
  - Clears Flask session cookie
  - Invalidates AdminSession record (for admins)
  - Clears session data from server

### Interaction with Existing Features
- **Admin Concurrent Logout**: `session-monitor.js` (100ms polling)
  - Both monitors can run simultaneously
  - Inactivity monitor checks server session validity via `/logout`
  - Session monitor checks via `/api/check-session`
  
- **Service Worker**: Inactivity monitor works independently
  - Does not rely on service worker
  - Monitors activity events in main thread
  - Logout redirects browser normally

---

## Security Considerations

### ✅ Strengths
1. **Session Invalidation**: Backend clears session on `/logout`
2. **User-Friendly**: Warning shows 10 seconds before logout
3. **Responsive**: Detects inactivity across mouse, keyboard, scroll, touch, form input
4. **Global Coverage**: Works on every page where footer is included
5. **Graceful Degradation**: If JavaScript disabled, session timeout still works via server (if implemented)

### ⚠️ Limitations
1. **Client-Side Timeout**: Relies on JavaScript execution
   - Workaround: Backend should also enforce server-side timeout
   - Consider adding server-side session timeout validation
   
2. **Multiple Tabs**: Each tab has its own inactivity timer
   - User could keep one tab idle while using another tab
   - Solution: Use SharedWorker or ServerSentEvents to sync across tabs (future enhancement)

### 🔒 Recommendations
1. **Add Server-Side Session Timeout**: Implement session expiry in Flask
   - Set session cookie lifetime to 70 seconds
   - Validate `last_activity` timestamp on backend
   
2. **Sync Across Tabs**: Implement tab synchronization
   - Use `localStorage` or `SharedWorker`
   - Single inactivity timer for entire session
   
3. **Audit Logging**: Log logout events to database
   - Track when users are auto-logged out
   - Useful for security audits

---

## Future Enhancements

### 1. Server-Side Session Timeout
```python
# In Flask app.py
from datetime import datetime, timedelta

@app.before_request
def check_session_timeout():
    last_activity = session.get('last_activity')
    if last_activity:
        if datetime.now() - datetime.fromisoformat(last_activity) > timedelta(seconds=65):
            session.clear()
            return redirect('/login')
    session['last_activity'] = datetime.now().isoformat()
```

### 2. Cross-Tab Activity Sync
```javascript
// Sync activity across all tabs using localStorage
window.addEventListener('storage', (e) => {
    if (e.key === 'lastActivity') {
        // Another tab recorded activity
        // Reset this tab's timer too
        monitor.onUserActivity();
    }
});

// Record activity to localStorage (visible to other tabs)
document.addEventListener('mousemove', () => {
    localStorage.setItem('lastActivity', Date.now());
});
```

### 3. Configurable Inactivity Period
```python
# In routes/settings.py
INACTIVITY_TIMEOUT_SECONDS = config.get('INACTIVITY_TIMEOUT', 60)

# In templates/footer.html
<script>
    const timeout = {{ inactivity_timeout }};
    const monitor = new InactivityMonitor({
        inactivityTimeoutMs: timeout * 1000,
    });
</script>
```

---

## Deployment Checklist

- [x] Create `inactivity-monitor.js` file
- [x] Add script tag to `footer.html`
- [x] Test in development environment
- [ ] Test with multiple browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test with multiple user roles (admin, teacher, parent, bursar, secretary, headteacher)
- [ ] Test concurrent tabs/windows
- [ ] Test on mobile devices (touch events)
- [ ] Deploy to staging
- [ ] Monitor logs for issues
- [ ] Deploy to production
- [ ] Notify users of new auto-logout feature

---

## Support & Troubleshooting

### Issue: Warning dialog not showing
**Possible Cause**: `inactivity-monitor.js` not loading
**Solution**: 
1. Check browser console for errors
2. Verify script tag in `footer.html`
3. Check Network tab to see if JS file loads
4. Run `window.inactivityMonitor.getStatus()` to verify class exists

### Issue: User not logging out after 60 seconds
**Possible Cause**: Activity events still firing (listener issue)
**Solution**:
1. Open DevTools > Console
2. Look for `[INACTIVITY MONITOR]` messages
3. Check if `🎯 User activity detected` is logged constantly
4. Try manually: `window.inactivityMonitor.handleInactivityLogout()`

### Issue: Multiple logout redirects on same page
**Possible Cause**: Multiple InactivityMonitor instances created
**Solution**:
1. Verify `footer.html` only includes script once
2. Check for duplicate script tags
3. Look for console errors about monitor initialization

### Issue: Logout URL not working (404 error)
**Possible Cause**: `/logout` endpoint not found or requires parameters
**Solution**:
1. Test logout manually: visit `/logout` in browser
2. Check `routes/user_routes.py` for logout handler
3. Verify routing in `app.py`
4. Check if logout requires POST vs GET

---

## Questions?

For detailed information about the implementation:
- Backend session validation: `app.py` (`validate_admin_session` middleware)
- Frontend session monitoring: `static/js/session-monitor.js` (100ms polling)
- This feature: `static/js/inactivity-monitor.js`

Last Updated: 2025-01-13
