// Wrap everything after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Determine WebSocket protocol based on current page protocol
  const wsProtocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
  const ws = new WebSocket(`${wsProtocol}${location.host}/ws/chat`);

  let history = [];
  let resume = {};

  // DOM elements
  const chatEl = document.getElementById('chat');
  const input = document.getElementById('msg-input');
  const sendBtn = document.getElementById('send-btn');
  const fieldsEl = document.getElementById('fields');
  const dlBtn = document.getElementById('dl-btn');
  const errorEl = document.getElementById('error');

  // Debug log WebSocket events
  ws.addEventListener('open', () => console.log('WebSocket connected'));
  ws.addEventListener('close', (e) => console.log('WebSocket closed', e));
  ws.addEventListener('error', (e) => console.error('WebSocket error', e));

  ws.addEventListener('message', ({ data }) => {
    console.log('Received message', data);
    clearError();
    let payload;
    try { payload = JSON.parse(data); }
    catch (e) { showError('Invalid JSON from server'); return; }

    const { message, data: resume_data } = payload;
    append('assistant', message);
    if (resume_data) {
      resume = resume_data;
      renderFields(resume_data);
      const complete = Object.keys(resume_data).every(k => {
        const v = resume_data[k];
        return v && (!(Array.isArray(v)) || v.length > 0);
      });
      if (complete) dlBtn.classList.remove('hidden');
    }
  });

  // Utility
  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove('hidden');
  }
  function clearError() {
    errorEl.textContent = '';
    errorEl.classList.add('hidden');
  }

  // Send logic
  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); send(); } });

  function send() {
    console.log('Sending message');
    clearError();
    if (ws.readyState !== WebSocket.OPEN) {
      showError('WebSocket not open');
      return;
    }
    const msg = input.value.trim();
    if (!msg) return;
    append('user', msg);
    history.push({ user: msg });
    try {
      ws.send(JSON.stringify({ message: msg, history }));
    } catch (e) {
      console.error('Send failed', e);
      showError('Send failed');
    }
    input.value = '';
  }

  function append(who, text) {
    const wrapper = document.createElement('div');
    wrapper.className = who === 'user' ? 'text-right' : 'text-left';
    wrapper.innerHTML = `
      <div class="chat chat-${who === 'user' ? 'end' : 'start'}">
        <div class="chat-bubble">${text}</div>
      </div>`;
    chatEl.appendChild(wrapper);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function renderFields(data) {
    fieldsEl.innerHTML = '';
    for (const key in data) {
      const val = Array.isArray(data[key]) ? data[key].join(', ') : data[key];
      fieldsEl.innerHTML += `
        <div>
          <label class="block font-semibold">${key}</label>
          <input class="input input-bordered w-full" value="${val}" readonly />
        </div>`;
    }
  }

  // Download logic
  dlBtn.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/download', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(resume)
      });
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'resume.md'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Download error', e);
      showError('Download failed');
    }
  });
});



















