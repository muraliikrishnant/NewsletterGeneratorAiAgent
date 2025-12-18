// Sophisticated frontend logic for Newsletter Studio
const API_BASE = window.API_BASE || 'http://127.0.0.1:8000';
const el = id => document.getElementById(id);

// UI helpers
function toast(message, type = 'info') {
  const t = el('toast');
  t.innerHTML = `<div class="card ${type} p-4"><div class="text-sm">${message}</div></div>`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3500);
}

function setChip(id, text, variant = 'info') {
  const c = el(id);
  c.textContent = text;
  c.className = `chip ${variant}`;
}

function setStatus(text) {
  el('status').textContent = text;
}

// Theme toggle
el('themeToggle').addEventListener('click', () => {
  document.documentElement.classList.toggle('dark');
});

// Sync words range and input
const wordsRange = el('wordsRange');
const wordsInput = el('words');
wordsRange.addEventListener('input', () => { wordsInput.value = wordsRange.value; localStorage.setItem('tars_words', wordsRange.value); });
wordsInput.addEventListener('input', () => { wordsRange.value = wordsInput.value; localStorage.setItem('tars_words', wordsInput.value); });

// Restore prompt/words from localStorage
el('prompt').value = localStorage.getItem('tars_prompt') || '';
const savedWords = localStorage.getItem('tars_words');
if (savedWords) { wordsRange.value = savedWords; wordsInput.value = savedWords; }
el('prompt').addEventListener('input', e => localStorage.setItem('tars_prompt', e.target.value));

// Build (dry-run)
el('build').addEventListener('click', async () => {
  const prompt = el('prompt').value.trim();
  const words = parseInt(wordsInput.value || '800', 10);
  if (!prompt) { toast('Enter a prompt to build.', 'error'); return; }
  setStatus('Building (dry-run)...');
  setChip('chipBuilt', 'Building…', 'info');
  try {
    const resp = await fetch(`${API_BASE}/build`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ prompt, words })
    });
    const ct = resp.headers.get('content-type') || '';
    if (!resp.ok) {
      const txt = await resp.text();
      toast(`Build failed ${resp.status}: ${txt.substring(0,200)}`, 'error');
      setChip('chipBuilt', 'Build failed', 'warn');
      return;
    }
    if (ct.includes('application/json')) {
      const data = await resp.json();
      el('subject').textContent = data.subject || 'Newsletter';
      el('preview').srcdoc = data.html || '';
      window.__lastBuiltHTML = data.html || '';
      window.__lastBuiltSubject = data.subject || 'Newsletter';
      el('download').disabled = !window.__lastBuiltHTML;
      setStatus('Built. Preview updated.');
      setChip('chipBuilt', 'Built', 'success');
      toast('Build complete.', 'success');
    } else {
      const txt = await resp.text();
      el('preview').srcdoc = txt;
      setStatus('Built (raw). Preview updated.');
      setChip('chipBuilt', 'Built (raw)', 'success');
    }
  } catch (e) {
    toast('Build error: ' + e.message, 'error');
    setChip('chipBuilt', 'Build error', 'warn');
  }
});

// Send via HITL (can be long-running)
el('send').addEventListener('click', async () => {
  const prompt = el('prompt').value.trim();
  const words = parseInt(wordsInput.value || '800', 10);
  if (!prompt) { toast('Enter a prompt before sending.', 'error'); return; }
  setStatus('Sending draft and entering HITL… This may take a while.');
  setChip('chipSent', 'Sending…', 'info');
  try {
    const resp = await fetch(`${API_BASE}/send`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ prompt, words })
    });
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const data = await resp.json();
      el('subject').textContent = data.subject || 'Newsletter';
      el('preview').srcdoc = data.html || '';
      setStatus('Send complete. See status panel for approval.');
      setChip('chipSent', 'Draft sent', 'success');
      toast('Draft sent for HITL review.', 'success');
    } else {
      const txt = await resp.text();
      toast(`Send returned ${resp.status}: ${txt.substring(0,200)}`, 'error');
      setChip('chipSent', 'Send error', 'warn');
    }
  } catch (e) {
    toast('Send error: ' + e.message, 'error');
    setChip('chipSent', 'Send error', 'warn');
  }
});

// Download built HTML
el('download').addEventListener('click', () => {
  const html = window.__lastBuiltHTML;
  const subject = window.__lastBuiltSubject || 'Newsletter';
  if (!html) { toast('Nothing to download. Build first.', 'warn'); return; }
  const blob = new Blob([html], { type: 'text/html' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${subject.replace(/[^a-z0-9\-_]+/gi,'_')}.html`;
  a.click();
  URL.revokeObjectURL(a.href);
});

// Publish (WordPress) — relies on backend env + local generated HTML files
el('publish').addEventListener('click', async () => {
  const token = prompt('Enter approved token (from hitl_status.json):');
  if (!token) return;
  setStatus('Publishing…');
  try {
    const resp = await fetch(`${API_BASE}/publish`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ token })
    });
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const data = await resp.json();
      if (data.url) {
        setStatus('Published successfully.');
        toast(`Published: ${data.url}`, 'success');
      } else {
        toast('Publish succeeded but no URL returned.', 'info');
      }
    } else {
      const txt = await resp.text();
      toast(`Publish response ${resp.status}: ${txt.substring(0,200)}`, 'error');
    }
  } catch (e) {
    toast('Publish error: ' + e.message, 'error');
  }
});

// Poll /status every 5s
async function pollStatus() {
  try {
    const resp = await fetch(`${API_BASE}/status`, { method: 'GET' });
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const s = await resp.json();
      const txt = (s.status || 'none');
      setStatus(`Status: ${txt}`);
      el('statusPanel').innerHTML = `
        <div class="text-sm">Status: <span class="font-medium">${s.status || 'none'}</span></div>
        ${s.subject ? `<div class="text-xs mt-1">Subject: ${s.subject}</div>`:''}
        ${s.recipients ? `<div class="text-xs mt-1">Recipients: ${(s.recipients||[]).join(', ')}</div>`:''}
        ${s.feedback ? `<div class="text-xs mt-1">Feedback: ${s.feedback}</div>`:''}
        <div class="text-[11px] mt-2 text-slate-500">Updated: ${s.updated_at ? new Date(s.updated_at*1000).toLocaleString() : 'n/a'}</div>
      `;
      // Chip updates
      if (txt === 'waiting') { setChip('chipSent', 'Waiting approval', 'info'); setChip('chipApproved', 'Not approved', 'info'); }
      if (txt === 'approved') { setChip('chipApproved', 'Approved', 'success'); }
      if (txt === 'feedback_received') { setChip('chipSent', 'Feedback received', 'info'); }
      if (txt === 'timeout' || txt === 'sent_unapproved') { setChip('chipApproved', 'Unapproved final sent', 'warn'); }
    } else {
      const txt = await resp.text();
      setStatus(`Status raw: ${txt.substring(0,120)}`);
    }
  } catch (e) {
    // don't spam toast
  }
}
setInterval(pollStatus, 5000);
pollStatus();
