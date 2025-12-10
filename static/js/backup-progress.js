// Shared backup progress utilities (createBackupProgress, CSRF helpers, SSE attach)
(function(){
    function getCookie(name) {
        try {
            const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
            return v ? decodeURIComponent(v.pop()) : null;
        } catch (e) { return null; }
    }

    function getCSRFToken() {
        const metaNames = ['csrf-token', 'csrf_token', 'csrf-token-value', 'csrfmiddlewaretoken'];
        for (const n of metaNames) {
            const m = document.querySelector('meta[name="' + n + '"]');
            if (m && m.content) return m.content;
        }
        const cookieNames = ['csrf_token', 'XSRF-TOKEN', 'csrf-token', 'csrftoken'];
        for (const c of cookieNames) {
            const val = getCookie(c);
            if (val) return val;
        }
        if (window.__csrf_token) return window.__csrf_token;
        return null;
    }

    function getCSRFHeaders() {
        const token = getCSRFToken();
        if (!token) return {};
        return { 'X-CSRFToken': token, 'X-CSRF-Token': token };
    }

    // Create a small vertical progress rail appended to a target element
    function createBackupProgress(targetEl){
        try{
            const wrapper = document.createElement('div');
            wrapper.className = 'backup-progress';
            wrapper.innerHTML = `<div class="rail"><div class="fill"></div></div><div class="percent">0%</div>`;

            // Use fixed positioning instead of absolute for better visibility
            wrapper.style.position = 'fixed';
            wrapper.style.left = '12px';
            wrapper.style.top = '120px';
            wrapper.style.width = '14px';
            wrapper.style.height = '80px';
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'flex-end';
            wrapper.style.gap = '6px';
            wrapper.style.zIndex = '9999';
            wrapper.style.pointerEvents = 'none';

            document.body.appendChild(wrapper);
            console.log('[BackupProgress] Progress bar created and appended to body');

            const fill = wrapper.querySelector('.fill');
            const percentEl = wrapper.querySelector('.percent');
            let current = 0;
            let timer = null;

            function set(p){
                current = Math.max(0, Math.min(100, Math.round(p)));
                fill.style.height = current + '%';
                percentEl.textContent = current + '%';
                console.log('[BackupProgress] Progress updated:', current + '%');
            }

            function startAuto(){
                if (timer) return;
                console.log('[BackupProgress] Auto-increment started');
                timer = setInterval(() => {
                    const delta = Math.max(1, Math.floor(Math.random()*5));
                    if (current < 60) set(current + delta + 2);
                    else if (current < 85) set(current + Math.floor(Math.random()*3) + 1);
                    else if (current < 97) set(current + 1);
                }, 400);
            }

            function stopAuto(){ if (timer){ clearInterval(timer); timer = null; console.log('[BackupProgress] Auto-increment stopped'); } }

            function done(success){
                stopAuto();
                set(100);
                if (!success){ fill.style.background = 'linear-gradient(180deg,#fca5a5,#ef4444)'; }
                console.log('[BackupProgress] Done - success:', success);
                setTimeout(() => {
                    try{
                        wrapper.remove();
                        console.log('[BackupProgress] Progress bar removed');
                    }catch(e){}
                }, 900);
            }

            return { set, startAuto, stopAuto, done, el: wrapper };
        }catch(e){ console.warn('createBackupProgress error', e); return null; }
    }

    // Attach an SSE (EventSource) to receive progress updates for a job id
    function attachBackupProgressSSE(jobId, prog){
        if (!jobId) return null;
        const url = `/admin/backup-maintenance/backup-progress-sse/${jobId}`;
        let es;
        try {
            es = new EventSource(url, { withCredentials: true });
            console.log('[SSE] EventSource created for URL:', url);
        } catch (e){
            console.warn('[SSE] EventSource not available:', e);
            return null;
        }

        es.onopen = function(ev){
            console.log('[SSE] Connection opened for job', jobId);
        };

        es.onmessage = function(ev){
            try{
                console.log('[SSE] Message received:', ev.data.substring(0, 100));
                const payload = JSON.parse(ev.data);
                if (payload && payload.progress){
                    const p = payload.progress;
                    console.log('[SSE] Progress update:', p.percent, '%', p.status);
                    if (prog && typeof prog.set === 'function') prog.set(p.percent || 0);
                    if (p.status === 'finished' || (p.percent && p.percent >= 100)){
                        console.log('[SSE] Backup finished, closing connection');
                        if (prog) prog.done(p.result && p.result.success);
                        es.close();
                    }
                }
            }catch(e){ console.error('[SSE] Parse error:', e); }
        };

        es.onerror = function(e){
            console.error('[SSE] Connection error:', {
                type: e.type,
                readyState: es.readyState,
                message: e.message,
                url: es.url
            });
            // readyState: 0=CONNECTING, 1=OPEN, 2=CLOSED
            // If CLOSED (2), don't attempt reconnect
            if (es.readyState === 2) {
                console.warn('[SSE] Connection permanently closed');
                es.close();
            }
        };

        return es;
    }

    // Start backup: POST to trigger endpoint, then attach SSE using returned job_id
    async function startBackupWithSSE(triggerUrl, targetEl){
        console.log('[startBackupWithSSE] Starting backup...');
        const btn = targetEl && targetEl.querySelector && targetEl.querySelector('.btn-trigger-backup') ? targetEl.querySelector('.btn-trigger-backup') : document.querySelector('.btn-trigger-backup');
        if (btn) {
            btn.disabled = true;
            var originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creating backup...';
        }

        const parentSection = (targetEl && targetEl.closest && targetEl.closest('.form-section')) || document.querySelector('.form-section') || document.querySelector('.main-content');
        const prog = createBackupProgress(parentSection);
        console.log('[startBackupWithSSE] Progress object created:', prog ? 'yes' : 'no');
        if (prog) prog.startAuto();

        try{
            console.log('[startBackupWithSSE] Posting to:', triggerUrl);
            const res = await fetch(triggerUrl, { method: 'POST', headers: Object.assign({ 'Content-Type':'application/json' }, getCSRFHeaders()) });
            console.log('[startBackupWithSSE] Response status:', res.status);
            const body = await res.json();
            console.log('[startBackupWithSSE] Response body:', body);

            if (res.status === 202 && body && body.job_id){
                const jobId = body.job_id;
                console.log('[startBackupWithSSE] Job ID received:', jobId);
                const es = attachBackupProgressSSE(jobId, prog);
                console.log('[startBackupWithSSE] SSE attached:', es ? 'yes' : 'no');

                // as a fallback, poll once every 2s if SSE isn't supported
                if (!es){
                    console.log('[startBackupWithSSE] No SSE, starting polling fallback...');
                    const poll = setInterval(async ()=>{
                        try{
                            const r = await fetch(`/admin/backup-maintenance/backup-progress/${jobId}`);
                            const j = await r.json();
                            console.log('[startBackupWithSSE] Poll result:', j);
                            if (j && j.success && j.progress){
                                prog.set(j.progress.percent || 0);
                                if (j.progress.status === 'finished' || j.progress.percent >= 100){
                                    clearInterval(poll);
                                    prog.done(j.progress.result && j.progress.result.success);
                                }
                            }
                        }catch(e){ console.warn('fallback poll error', e); }
                    }, 2000);
                }

                // when job finishes, re-enable button and reload history
                // we'll rely on SSE or poll to call prog.done(); watch progress store via a short interval to re-enable button
                const waiter = setInterval(async ()=>{
                    try{
                        const r = await fetch(`/admin/backup-maintenance/backup-progress/${jobId}`);
                        const j = await r.json();
                        console.log('[startBackupWithSSE] Waiter check:', j);
                        if (j && j.success && j.progress && (j.progress.status === 'finished' || j.progress.percent >= 100)){
                            clearInterval(waiter);
                            if (btn){ btn.disabled = false; btn.innerHTML = originalHTML; }
                            // show toast if result available
                            if (j.progress.result){
                                const resObj = j.progress.result;
                                if (resObj.success) {
                                    if (window.showToast) showToast('success','Backup Successful! ✅', (resObj.filename || '') + ' ' + (resObj.file_size || ''));
                                    if (window.loadBackupHistory) loadBackupHistory();
                                    // Refresh the "Last Backup" display with new timestamp
                                    if (window.refreshBackupSettings) setTimeout(() => window.refreshBackupSettings(), 500);
                                } else {
                                    if (window.showToast) showToast('error','Backup Failed ❌', resObj.message || 'Backup job failed');
                                }
                            } else {
                                if (window.loadBackupHistory) loadBackupHistory();
                                // Refresh the "Last Backup" display even if no explicit result
                                if (window.refreshBackupSettings) setTimeout(() => window.refreshBackupSettings(), 500);
                            }
                        }
                    }catch(e){ console.warn('waiter error', e); }
                }, 800);

            } else {
                // fallback: server returned immediate response
                console.log('[startBackupWithSSE] No 202 response, using fallback');
                if (prog) prog.done(body && body.success);
                if (body && body.success){ if (window.showToast) showToast('success','Backup Successful! ✅', `${body.filename || ''}`); if (window.loadBackupHistory) loadBackupHistory(); }
                else { if (window.showToast) showToast('error','Backup Failed ❌', body && body.message ? body.message : 'Unknown error'); }
                if (btn){ btn.disabled = false; btn.innerHTML = originalHTML; }
            }
        }catch(e){
            console.error('startBackupWithSSE error', e);
            if (prog) prog.done(false);
            if (btn){ btn.disabled = false; btn.innerHTML = originalHTML; }
            if (window.showToast) showToast('error','Error ❌', e.message || 'An unexpected error occurred');
        }
    }

    // expose to window
    window.createBackupProgress = createBackupProgress;
    window.getCSRFToken = getCSRFToken;
    window.getCSRFHeaders = getCSRFHeaders;
    window.attachBackupProgressSSE = attachBackupProgressSSE;
    window.startBackupWithSSE = startBackupWithSSE;

    // Refresh the "Last Backup" display from server
    window.refreshBackupSettings = async function() {
        try {
            const resp = await fetch('/admin/api/backup-settings');
            const data = await resp.json();
            if (data.success && data.last_backup_time) {
                const el = document.getElementById('last-backup-time');
                if (el) {
                    // Server returns East African format: DD/MM/YYYY HH:MM:SS AM/PM
                    el.textContent = data.last_backup_time;
                    console.log('[refreshBackupSettings] Updated last backup time to:', data.last_backup_time);
                }
            }
        } catch (e) {
            console.warn('[refreshBackupSettings] Error:', e);
        }
    };
})();
