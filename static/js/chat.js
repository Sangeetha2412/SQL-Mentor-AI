/**
 * chat.js - Full Chat Interface Logic
 */

let currentChatId = null;
let selectedFileIds = [];
let isGenerating = false;

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatTitle = document.getElementById('chat-title-display');
const fileChipsBar = document.getElementById('file-chips-bar');
const typingIndicator = document.getElementById('typing-indicator');
const welcomeScreen = document.getElementById('welcome-screen');

// ── Auto-resize textarea ──
chatInput?.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});

// ── Send on Enter (Shift+Enter for newline) ──
chatInput?.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

sendBtn?.addEventListener('click', sendMessage);

async function sendMessage() {
  const msg = chatInput?.value.trim();
  if (!msg || isGenerating) return;

  isGenerating = true;
  sendBtn.disabled = true;
  chatInput.value = '';
  chatInput.style.height = 'auto';

  if (welcomeScreen) welcomeScreen.style.display = 'none';

  appendMessage('user', msg);
  showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, chat_id: currentChatId, file_ids: selectedFileIds })
    });
    const data = await res.json();

    hideTyping();

    if (data.chat_id && !currentChatId) {
      currentChatId = data.chat_id;
      refreshSidebar();
    }

    appendMessage('assistant', data.response, data.sources || []);
    if (chatTitle && data.chat_id) chatTitle.textContent = 'Chat #' + data.chat_id;
  } catch (e) {
    hideTyping();
    appendMessage('assistant', '⚠️ Connection error. Please try again.', []);
  }

  isGenerating = false;
  sendBtn.disabled = false;
  chatInput.focus();
}

function appendMessage(role, content, sources = []) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const initials = role === 'user'
    ? (window.USER_NAME || 'U').charAt(0).toUpperCase()
    : '🤖';

  const sourcesHtml = sources.length
    ? `<div class="msg-sources">${sources.map(s => `<span class="source-chip"><i class="fa-solid fa-file-lines"></i>${s}</span>`).join('')}</div>`
    : '';

  const renderedContent = role === 'assistant'
    ? (window.marked ? marked.parse(content) : escapeHtml(content))
    : `<span>${escapeHtml(content)}</span>`;

  row.innerHTML = `
    <div class="msg-avatar ${role === 'user' ? 'user-av' : 'ai-av'}">${initials}</div>
    <div class="msg-content">
      <div class="msg-bubble">${renderedContent}</div>
      ${sourcesHtml}
      <div class="msg-actions">
        <button class="msg-action-btn" onclick="copyMsgContent(this)"><i class="fa-regular fa-copy"></i> Copy</button>
      </div>
      <div class="msg-time">${new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</div>
    </div>`;

  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Add copy buttons to code blocks
  row.querySelectorAll('pre').forEach(pre => {
    if (!pre.querySelector('.copy-btn')) {
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
      btn.onclick = () => {
        const code = pre.querySelector('code');
        copyToClipboard(code ? code.textContent : pre.textContent, btn);
      };
      pre.appendChild(btn);
    }
  });
}

function copyMsgContent(btn) {
  const bubble = btn.closest('.msg-content').querySelector('.msg-bubble');
  copyToClipboard(bubble.innerText, btn);
}

function showTyping() {
  if (typingIndicator) typingIndicator.style.display = 'flex';
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function hideTyping() {
  if (typingIndicator) typingIndicator.style.display = 'none';
}

function escapeHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── New Chat ──
document.getElementById('new-chat-btn')?.addEventListener('click', async () => {
  currentChatId = null;
  selectedFileIds = [];
  renderFileChips();
  chatMessages.innerHTML = '';
  if (welcomeScreen) welcomeScreen.style.display = 'flex';
  if (chatTitle) chatTitle.textContent = 'New Chat';
  document.querySelectorAll('.chat-history-item').forEach(i => i.classList.remove('active'));
  chatInput?.focus();
});

// ── Load Chat ──
async function loadChat(chatId) {
  currentChatId = chatId;
  chatMessages.innerHTML = '';
  if (welcomeScreen) welcomeScreen.style.display = 'none';

  document.querySelectorAll('.chat-history-item').forEach(i => {
    i.classList.toggle('active', i.dataset.chatId == chatId);
  });

  try {
    const data = await apiGet(`/api/chat-messages/${chatId}`);
    if (chatTitle) chatTitle.textContent = data.title || 'Chat';
    data.messages.forEach(m => appendMessage(m.role, m.content, m.sources || []));
  } catch (e) {
    showToast('Failed to load chat', 'error');
  }
}

// ── Delete Chat ──
async function deleteChat(chatId, e) {
  e.stopPropagation();
  if (!confirm('Delete this chat?')) return;
  await apiPost('/api/delete-chat', { chat_id: chatId });
  if (chatId == currentChatId) {
    currentChatId = null;
    chatMessages.innerHTML = '';
    if (welcomeScreen) welcomeScreen.style.display = 'flex';
  }
  refreshSidebar();
}

// ── Rename Chat ──
async function renameChat(chatId, e) {
  e.stopPropagation();
  const title = prompt('New chat title:');
  if (!title) return;
  await apiPost('/api/rename-chat', { chat_id: chatId, title });
  refreshSidebar();
}

// ── Sidebar refresh ──
async function refreshSidebar() {
  const data = await apiGet('/api/chat-history');
  const container = document.getElementById('chat-history-list');
  if (!container) return;
  const search = document.getElementById('sidebar-search')?.value.toLowerCase() || '';
  const filtered = data.filter(c => c.title.toLowerCase().includes(search));
  container.innerHTML = filtered.map(c => `
    <div class="chat-history-item ${c.id == currentChatId ? 'active' : ''}" data-chat-id="${c.id}" onclick="loadChat(${c.id})">
      <i class="fa-regular fa-message chat-history-icon"></i>
      <span class="chat-history-title">${escapeHtml(c.title)}</span>
      <div class="chat-item-actions">
        <button class="chat-action-btn" onclick="renameChat(${c.id}, event)" title="Rename"><i class="fa-solid fa-pencil"></i></button>
        <button class="chat-action-btn" onclick="deleteChat(${c.id}, event)" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    </div>`).join('');
}

document.getElementById('sidebar-search')?.addEventListener('input', refreshSidebar);

// ── File Selector ──
document.getElementById('file-attach-btn')?.addEventListener('click', () => {
  document.getElementById('file-picker-dropdown')?.classList.toggle('show');
});

document.addEventListener('click', e => {
  const dropdown = document.getElementById('file-picker-dropdown');
  if (dropdown && !e.target.closest('#file-attach-btn') && !e.target.closest('#file-picker-dropdown')) {
    dropdown.classList.remove('show');
  }
});

function toggleFileSelection(fileId, filename, checkbox) {
  if (checkbox.checked) {
    if (!selectedFileIds.includes(fileId)) selectedFileIds.push(fileId);
  } else {
    selectedFileIds = selectedFileIds.filter(id => id !== fileId);
  }
  renderFileChips();
}

function renderFileChips() {
  if (!fileChipsBar) return;
  const allFiles = window.USER_FILES || [];
  fileChipsBar.innerHTML = selectedFileIds.map(id => {
    const f = allFiles.find(x => x.id == id);
    if (!f) return '';
    return `<div class="file-chip">
      <i class="fa-solid fa-paperclip"></i>${f.name}
      <button class="file-chip-remove" onclick="removeFileChip(${id})">✕</button>
    </div>`;
  }).join('');
}

function removeFileChip(fileId) {
  selectedFileIds = selectedFileIds.filter(id => id !== fileId);
  const cb = document.querySelector(`input[data-file-id="${fileId}"]`);
  if (cb) cb.checked = false;
  renderFileChips();
}

// ── Quick prompts ──
document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (chatInput) { chatInput.value = btn.dataset.prompt || btn.textContent.trim(); chatInput.focus(); }
  });
});

document.querySelectorAll('.quick-action-card').forEach(card => {
  card.addEventListener('click', () => {
    if (chatInput) { chatInput.value = card.dataset.prompt || ''; chatInput.focus(); }
    if (welcomeScreen) welcomeScreen.style.display = 'none';
  });
});

// ── Sidebar mobile toggle ──
document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
  document.querySelector('.chat-sidebar')?.classList.toggle('open');
});

// ── Init ──
refreshSidebar();
