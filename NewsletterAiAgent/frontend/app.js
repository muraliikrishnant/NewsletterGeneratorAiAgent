// VERSION: 2.0.3 - FRONTEND HITL + THEME TOGGLE FIXES
// Sophisticated frontend logic for Newsletter Studio
const el = id => document.getElementById(id);

// Auto-detect API base: check input field first, then default to current host or localhost
function getApiBase() {
  const customUrl = el('backendUrl') ? el('backendUrl').value.trim() : '';
  if (customUrl) return customUrl.replace(/\/$/, "");

  if (window.API_BASE) return window.API_BASE.replace(/\/$/, "");
  if (window.location.hostname.includes('onrender.com')) {
    return window.location.origin;
  }
  return 'http://127.0.0.1:8000';
}

// UI helpers
function toast(message, type = 'info') {
  const t = el('toast');
  if (!t) return;
  t.innerHTML = `<div class="card ${type} p-4 shadow-xl border-l-4 ${type === 'error' ? 'border-red-500 bg-red-50' : type === 'success' ? 'border-green-500 bg-green-50' : 'border-indigo-500 bg-indigo-50'} rounded-lg animate-in slide-in-from-right"><div class="text-sm font-medium ${type === 'error' ? 'text-red-800' : type === 'success' ? 'text-green-800' : 'text-indigo-800'}">${message}</div></div>`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 5000);
}

function setChip(id, text, variant = 'info') {
  const c = el(id);
  if (!c) return;
  c.textContent = text;
  c.className = `chip ${variant}`;
}

function setStatus(text) {
  const statusEl = el('status');
  if (statusEl) statusEl.textContent = text;
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  const promptEl = el('prompt');
  const wordsRange = el('wordsRange');
  const wordsInput = el('words');
  const previewEl = el('preview');
  const subEl = el('subject');
  const backendUrlInput = el('backendUrl');
  let lastStatusTs = 0;
  let minStatusTs = 0;

  function setPreview(html, subject) {
    if (subEl && subject) subEl.textContent = subject;
    if (previewEl) previewEl.srcdoc = html || '';
  }

  function clearPreview() {
    if (subEl) subEl.textContent = 'Ready to build...';
    if (previewEl) previewEl.srcdoc = '';
  }

  // Load backend URL from storage if exists
  const savedUrl = localStorage.getItem('tars_backend_url');
  if (savedUrl && backendUrlInput) backendUrlInput.value = savedUrl;
  if (backendUrlInput) {
    backendUrlInput.addEventListener('input', e => localStorage.setItem('tars_backend_url', e.target.value));
  }

  // Theme toggle
  const themeToggle = el('themeToggle');
  const savedTheme = localStorage.getItem('tars_theme') || 'light';
  document.documentElement.classList.toggle('dark', savedTheme === 'dark');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const isDark = document.documentElement.classList.toggle('dark');
      localStorage.setItem('tars_theme', isDark ? 'dark' : 'light');
    });
  }

  // Sync words range and input
  if (wordsRange && wordsInput) {
    wordsRange.addEventListener('input', () => {
      wordsInput.value = wordsRange.value;
      localStorage.setItem('tars_words', wordsRange.value);
    });
    wordsInput.addEventListener('input', () => {
      wordsRange.value = wordsInput.value;
      localStorage.setItem('tars_words', wordsInput.value);
    });
  }

  // Restore prompt/words from localStorage
  if (promptEl) {
    promptEl.value = localStorage.getItem('tars_prompt') || '';
    promptEl.addEventListener('input', e => localStorage.setItem('tars_prompt', e.target.value));
  }
  const savedWords = localStorage.getItem('tars_words');
  if (savedWords && wordsRange && wordsInput) {
    wordsRange.value = savedWords;
    wordsInput.value = savedWords;
  }

  // Build (dry-run)
  const buildBtn = el('build');
  if (buildBtn) {
    buildBtn.addEventListener('click', async () => {
      const prompt = promptEl ? promptEl.value.trim() : '';
      const words = parseInt(wordsInput ? wordsInput.value : '300', 10);
      if (!prompt) {
        toast('Enter a topic or topic context to build.', 'error');
        return;
      }
      clearPreview();
      lastStatusTs = 0;
      minStatusTs = Math.floor(Date.now() / 1000);
      setStatus('Generating initial newsletter... Please wait.');
      setChip('chipBuilt', 'Building…', 'info');
      try {
        const resp = await fetch(`${getApiBase()}/build`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, words })
        });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(`Build failed (${resp.status}): ${txt.substring(0, 100)}`);
        }
        const data = await resp.json();
        setPreview(data.html || '', data.subject || 'Newsletter');
        setStatus('Newsletter Generated (Local Preview).');
        setChip('chipBuilt', 'Built', 'success');
        toast('Draft generated successfully.', 'success');
      } catch (e) {
        toast(e.message, 'error');
        setChip('chipBuilt', 'Build error', 'warn');
      }
    });
  }

  // Send via HITL
  const sendBtn = el('send');
  if (sendBtn) {
    sendBtn.addEventListener('click', async () => {
      const prompt = promptEl ? promptEl.value.trim() : '';
      const words = parseInt(wordsInput ? wordsInput.value : '300', 10);
      if (!prompt) {
        toast('Enter a topic before starting HITL.', 'error');
        return;
      }
      clearPreview();
      lastStatusTs = 0;
      minStatusTs = Math.floor(Date.now() / 1000);
      setStatus('Starting Human-in-the-Loop process...');
      setChip('chipSent', 'Starting…', 'info');
      try {
        const resp = await fetch(`${getApiBase()}/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, words })
        });
        if (!resp.ok) throw new Error('Failed to start HITL process.');
        const data = await resp.json();
        setPreview(data.html || '', data.subject || 'Newsletter');
        setStatus('HITL Started. Review draft below.');
        setChip('chipSent', 'HITL Active', 'success');
        toast('HITL process started. Check the box below the preview.', 'success');
        pollStatus();
      } catch (e) {
        toast(e.message, 'error');
        setChip('chipSent', 'Error', 'warn');
      }
    });
  }

  // Approve
  const approveBtn = el('approveBtn');
  if (approveBtn) {
    approveBtn.addEventListener('click', async () => {
      setStatus('Finalizing and sending email...');
      try {
        const resp = await fetch(`${getApiBase()}/approve`, { method: 'POST' });
        if (!resp.ok) throw new Error('Final approval failed.');
        toast('Approved! Final draft sent to your email.', 'success');
        setStatus('Process Complete. Final Email Sent.');
        setChip('chipApproved', 'Approved', 'success');
        pollStatus();
      } catch (e) {
        toast(e.message, 'error');
      }
    });
  }

  // Revise
  const reviseBtn = el('reviseBtn');
  if (reviseBtn) {
    reviseBtn.addEventListener('click', async () => {
      const feedback = el('feedback').value.trim();
      if (!feedback) {
        toast('Please enter some feedback for the AI.', 'warn');
        return;
      }
      setStatus('AI is revising the newsletter based on your feedback...');
      try {
        const resp = await fetch(`${getApiBase()}/revise`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ feedback })
        });
        if (!resp.ok) throw new Error('AI revision failed.');
        const data = await resp.json();
        setPreview(data.html || '', data.subject || 'Newsletter');
        toast('Newsletter revised successfully.', 'success');
        setStatus('Revised version ready for review.');
        el('feedback').value = '';
        pollStatus();
      } catch (e) {
        toast(e.message, 'error');
      }
    });
  }

  // Start polling status
  pollStatus();
  setInterval(pollStatus, 5000);

  async function pollStatus() {
    try {
      const resp = await fetch(`${getApiBase()}/status`, { method: 'GET' });
      if (!resp.ok) return;
      const s = await resp.json();
      const txt = s.status || 'none';

      if (txt === 'none') {
        clearPreview();
      }

      if (s.updated_at && s.updated_at < minStatusTs) return;
      if (s.updated_at && s.updated_at > lastStatusTs) {
        lastStatusTs = s.updated_at;
        if (s.subject || s.html) {
          setPreview(s.html || '', s.subject || 'Newsletter');
        }
      }

      const details = el('statusDetails');
      if (details) {
        details.innerHTML = `
        <div class="space-y-2">
            <div class="flex items-center justify-between text-xs">
                <span class="text-slate-500">Current Phase:</span>
                <span class="font-bold ${txt === 'waiting_approval' ? 'text-indigo-600' : 'text-slate-700'} uppercase tracking-tighter shadow-sm bg-slate-100 px-2 py-0.5 rounded">${txt.replace('_', ' ')}</span>
            </div>
            ${s.updated_at ? `<div class="text-[10px] text-slate-400 text-right">Updated: ${new Date(s.updated_at * 1000).toLocaleTimeString()}</div>` : ''}
        </div>
      `;
      }

      // Show/Hide HITL Box
      const hitlBox = el('hitlBox');
      if (hitlBox) {
        if (txt === 'waiting_approval') {
          hitlBox.classList.remove('hidden');
        } else {
          hitlBox.classList.add('hidden');
        }
      }

      // Chip & Global Status
      if (txt === 'waiting_approval') {
        setStatus('Waiting for your review/approval.');
        setChip('chipSent', 'HITL Active', 'success');
        setChip('chipApproved', 'Pending', 'info');
      } else if (txt === 'approved') {
        setStatus('Final newsletter approved and sent.');
        setChip('chipSent', 'Complete', 'success');
        setChip('chipApproved', 'Approved', 'success');
      }
    } catch (e) {
      // Fail silently for polling
    }
  }
});
