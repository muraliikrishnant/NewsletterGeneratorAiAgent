// Default to the local backend during development so starting both servers works
const API_BASE = window.API_BASE || 'http://127.0.0.1:8000'; // Set at deploy or use relative path

const el = id => document.getElementById(id);
const status = msg => { el('status').innerText = msg; };

el('build').addEventListener('click', async () => {
  const prompt = el('prompt').value.trim();
  const words = parseInt(el('words').value || '800', 10);
  if (!prompt) return status('Enter a prompt');
  status('Building (dry-run)...');
  try {
    const resp = await fetch(`${API_BASE}/build`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prompt, words})
    });
    let data;
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      data = await resp.json();
    } else {
      // fallback: try to read text (HTML/error page) and show it in preview
      const txt = await resp.text();
      status(`Build returned ${resp.status}. Showing raw response in preview.`);
      el('preview').srcdoc = txt;
      return;
    }
    status('Built. Preview below.');
    el('preview').srcdoc = data.html || '';
  } catch (e) {
    status('Build failed: ' + e.message);
  }
});

el('send').addEventListener('click', async () => {
  const prompt = el('prompt').value.trim();
  const words = parseInt(el('words').value || '800', 10);
  if (!prompt) return status('Enter a prompt');
  status('Sending draft and entering HITL...');
  try {
    const resp = await fetch(`${API_BASE}/send`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prompt, words})
    });
    let data;
    const ct2 = resp.headers.get('content-type') || '';
    if (ct2.includes('application/json')) {
      data = await resp.json();
      status('Draft sent. Token: ' + (data.token||'n/a'));
    } else {
      // Server returned non-JSON (maybe an HTML error page) — show useful info
      const txt = await resp.text();
      status(`Send returned ${resp.status}: ${txt.substring(0,200)}`);
    }
    // Optionally poll status endpoint
  } catch (e) {
    status('Send failed: ' + e.message);
  }
});

el('publish').addEventListener('click', async () => {
  const token = prompt('Enter approved token from hitl_status.json:');
  if (!token) return;
  status('Publishing to WordPress...');
  try {
    const resp = await fetch(`${API_BASE}/publish`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({token})
    });
    let data;
    const ct3 = resp.headers.get('content-type') || '';
    if (ct3.includes('application/json')) {
      data = await resp.json();
      status('Published. URL: ' + (data.url || 'n/a'));
    } else {
      const txt = await resp.text();
      status(`Publish returned ${resp.status}: ${txt.substring(0,200)}`);
    }
  } catch (e) {
    status('Publish failed: ' + e.message);
  }
});
