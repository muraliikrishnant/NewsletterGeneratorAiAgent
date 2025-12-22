// Sophisticated frontend logic for Newsletter Studio
// Auto-detect API base: use Render URL in production (GitHub Pages), otherwise localhost
const API_BASE = window.location.hostname.includes('github.io') || window.location.hostname.includes('onrender.com')
  ? 'https://newsletteraiagent-tars.onrender.com'
  : (window.API_BASE || 'http://127.0.0.1:8000');
const el = id => document.getElementById(id);

// UI helpers
function toast(message, type = 'info') {
  const t = el('toast');
  if (!t) return;
  t.innerHTML = \`<div class="card \${type} p-4"><div class="text-sm">\${message}</div></div>\`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3500);
}

function setChip(id, text, variant = 'info') {
  const c = el(id);
  if (!c) return;
  c.textContent = text;
  c.className = \`chip \${variant}\`;
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

  // Theme toggle
  const themeToggle = el('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
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
      const words = parseInt(wordsInput ? wordsInput.value : '800', 10);
      if (!prompt) {
        toast('Enter a prompt to build.', 'error');
        return;
      }
      setStatus('Building (dry-run)...');
      setChip('chipBuilt', 'Building…', 'info');
      try {
        const resp = await fetch(\`\${API_BASE}/build\`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, words })
        });
        const ct = resp.headers.get('content-type') || '';
        if (!resp.ok) {
          const txt = await resp.text();
          toast(\`Build failed \${resp.status}: \${txt.substring(0, 200)}\`, 'error');
          setChip('chipBuilt', 'Build failed', 'warn');
          return;
        }
        if (ct.includes('application/json')) {
          const data = await resp.json();
          if (subEl) subEl.textContent = data.subject || 'Newsletter';
          if (previewEl) previewEl.srcdoc = data.html || '';
          window.__lastBuiltHTML = data.html || '';
          window.__lastBuiltSubject = data.subject || 'Newsletter';
          const dlBtn = el('download');
          if (dlBtn) dlBtn.disabled = !window.__lastBuiltHTML;
          setStatus('Built. Preview updated.');
          setChip('chipBuilt', 'Built', 'success');
          toast('Build complete.', 'success');
        } else {
          const txt = await resp.text();
          if (previewEl) previewEl.srcdoc = txt;
          setStatus('Built (raw). Preview updated.');
          setChip('chipBuilt', 'Built (raw)', 'success');
        }
      } catch (e) {
        toast('Build error: ' + e.message, 'error');
        setChip('chipBuilt', 'Build error', 'warn');
      }
    });
  }

  // Send via HITL
  const sendBtn = el('send');
  if (sendBtn) {
    sendBtn.addEventListener('click', async () => {
      const prompt = promptEl ? promptEl.value.trim() : '';
      const words = parseInt(wordsInput ? wordsInput.value : '800', 10);
      if (!prompt) {
        toast('Enter a prompt before sending.', 'error');
        return;
      }
      setStatus('Generating draft… This may take a moment.');
      setChip('chipSent', 'Generating…', 'info');
      try {
        const resp = await fetch(\`\${API_BASE}/send\`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, words })
        });
        const ct = resp.headers.get('content-type') || '';
        if (resp.ok && ct.includes('application/json')) {
          const data = await resp.json();
          if (subEl) subEl.textContent = data.subject || 'Newsletter';
          if (previewEl) previewEl.srcdoc = data.html || '';
          setStatus('Draft generated. Please review and approve or revise.');
          setChip('chipSent', 'Draft ready', 'success');
          toast('Draft ready for your review.', 'success');
          pollStatus(); // Refresh immediately
        } else {
          const txt = await resp.text();
          toast(\`Send failed \${resp.status}: \${txt.substring(0, 200)}\`, 'error');
          setChip('chipSent', 'Send error', 'warn');
        }
      } catch (e) {
        toast('Send error: ' + e.message, 'error');
        setChip('chipSent', 'Send error', 'warn');
      }
    });
  }

  // Approve
  const approveBtn = el('approveBtn');
  if (approveBtn) {
    approveBtn.addEventListener('click', async () => {
      setStatus('Approving and sending final email…');
      try {
        const resp = await fetch(\`\${API_BASE}/approve\`, { method: 'POST' });
        if (resp.ok) {
          toast('Approved and final email sent!', 'success');
          setStatus('Approved. Final email sent.');
          setChip('chipApproved', 'Approved', 'success');
          pollStatus();
        } else {
          const txt = await resp.text();
          toast(\`Approval failed: \${txt}\`, 'error');
        }
      } catch (e) {
        toast('Approval error: ' + e.message, 'error');
      }
    });
  }

  // Revise
  const reviseBtn = el('reviseBtn');
  if (reviseBtn) {
    reviseBtn.addEventListener('click', async () => {
      const feedback = el('feedback').value.trim();
      if (!feedback) {
        toast('Please enter feedback for revision.', 'warn');
        return;
      }
      setStatus('Revising draft… This may take a moment.');
      try {
        const resp = await fetch(\`\${API_BASE}/revise\`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ feedback })
        });
        if (resp.ok) {
          const data = await resp.json();
          if (subEl) subEl.textContent = data.subject || 'Newsletter';
          if (previewEl) previewEl.srcdoc = data.html || '';
          toast('Revision complete.', 'success');
          setStatus('Revised. Please review again.');
          el('feedback').value = ''; // clear feedback
          pollStatus();
        } else {
          const txt = await resp.text();
          toast(\`Revision failed: \${txt}\`, 'error');
        }
      } catch (e) {
        toast('Revision error: ' + e.message, 'error');
      }
    });
  }

  // Download built HTML
  const downloadBtn = el('download');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const html = previewEl.srcdoc;
      const subject = subEl.textContent || 'Newsletter';
      if (!html) {
        toast('Nothing to download. Build first.', 'warn');
        return;
      }
      const blob = new Blob([html], { type: 'text/html' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = \`\${subject.replace(/[^a-z0-9\\-_]+/gi, '_')}.html\`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  // Publish to WordPress
  const publishBtn = el('publish');
  if (publishBtn) {
    publishBtn.addEventListener('click', async () => {
      const token = prompt('Enter placeholder token (or any string):');
      if (!token) return;
      setStatus('Publishing…');
      try {
        const resp = await fetch(\`\${API_BASE}/publish\`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token })
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.url) {
            setStatus('Published successfully.');
            toast(\`Published: \${data.url}\`, 'success');
          } else {
            toast('Publish succeeded but no URL returned.', 'info');
          }
        } else {
          const txt = await resp.text();
          toast(\`Publish failed: \${txt}\`, 'error');
        }
      } catch (e) {
        toast('Publish error: ' + e.message, 'error');
      }
    });
  }

  // Start polling status
  pollStatus();
  setInterval(pollStatus, 5000);
});

async function pollStatus() {
  try {
    const resp = await fetch(\`\${API_BASE}/status\`, { method: 'GET' });
    if (!resp.ok) return;
    const s = await resp.json();
    const txt = s.status || 'none';
    
    // Update labels if we are in HITL
    if (txt === 'waiting_approval' || txt === 'approved') {
        const subEl = el('subject');
        const previewEl = el('preview');
        if (subEl && s.subject) subEl.textContent = s.subject;
        if (previewEl && s.html && !previewEl.srcdoc) {
             previewEl.srcdoc = s.html;
        }
    }

    const details = el('statusDetails');
    if (details) {
      details.innerHTML = \`
        <div class="text-sm">Status: <span class="font-medium">\${txt}</span></div>
        \${s.subject ? \`<div class="text-xs mt-1">Subject: \${s.subject}</div>\` : ''}
        \${s.recipients ? \`<div class="text-xs mt-1">Recipients: \${(s.recipients || []).join(', ')}</div>\` : ''}
        \${s.feedback ? \`<div class="text-xs mt-1 italic text-slate-500">Last Feedback: \${s.feedback}</div>\` : ''}
        <div class="text-[11px] mt-2 text-slate-500">Updated: \${s.updated_at ? new Date(s.updated_at * 1000).toLocaleString() : 'n/a'}</div>
      \`;
    }

    // Show/Hide HITL controls
    const controls = el('hitlControls');
    if (controls) {
      if (txt === 'waiting_approval') {
        controls.classList.remove('hidden');
      } else {
        controls.classList.add('hidden');
      }
    }

    // Chip updates
    if (txt === 'waiting_approval') {
      setChip('chipSent', 'Waiting approval', 'info');
      setChip('chipApproved', 'Not approved', 'info');
    }
    if (txt === 'approved') {
      setChip('chipSent', 'Sent', 'success');
      setChip('chipApproved', 'Approved', 'success');
    }
    if (txt === 'feedback_received') {
      setChip('chipSent', 'Feedback received', 'info');
    }
  } catch (e) {
    // Silent fail for polling
  }
}
