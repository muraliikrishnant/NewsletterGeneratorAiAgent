const API_BASE = window.API_BASE || ''; // Set at deploy or use relative path

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
    const data = await resp.json();
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
    const data = await resp.json();
    status('Draft sent. Token: ' + (data.token||'n/a'));
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
    const data = await resp.json();
    status('Published. URL: ' + (data.url || 'n/a'));
  } catch (e) {
    status('Publish failed: ' + e.message);
  }
});
