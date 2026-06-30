/**
 * main.js - Global JavaScript utilities
 * Used across all pages for flash messages, modals, copy buttons, etc.
 */

// ─── Auto-dismiss flash messages ───
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash-msg');
  flashes.forEach(msg => {
    setTimeout(() => {
      msg.style.opacity = '0';
      msg.style.transform = 'translateX(100%)';
      msg.style.transition = 'all 0.3s ease';
      setTimeout(() => msg.remove(), 300);
    }, 4000);
  });
});

// ─── Copy button helper ───
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
    btn.style.background = 'rgba(34, 197, 94, 0.2)';
    setTimeout(() => {
      btn.innerHTML = original;
      btn.style.background = '';
    }, 2000);
  }).catch(() => {
    // Fallback for older browsers
    const el = document.createElement('textarea');
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    el.remove();
  });
}

// ─── Modal helpers ───
function showModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) {
    overlay.classList.add('show');
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) hideModal(modalId);
    }, { once: true });
  }
}

function hideModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) overlay.classList.remove('show');
}

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
  }
});

// ─── Format file size ───
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
  return (bytes / 1073741824).toFixed(1) + ' GB';
}

// ─── Show toast notification ───
function showToast(message, type = 'info') {
  const container = document.querySelector('.flash-container') || createFlashContainer();
  const toast = document.createElement('div');
  const icons = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle', warning: 'fa-exclamation-circle' };
  toast.className = `flash-msg flash-${type}`;
  toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function createFlashContainer() {
  const div = document.createElement('div');
  div.className = 'flash-container';
  document.body.appendChild(div);
  return div;
}

// ─── API helper ───
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

async function apiGet(url) {
  const res = await fetch(url);
  return res.json();
}

// ─── Add copy buttons to code blocks ───
function addCopyButtons() {
  document.querySelectorAll('pre:not(.has-copy)').forEach(pre => {
    pre.classList.add('has-copy');
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
    btn.onclick = () => {
      const code = pre.querySelector('code');
      copyToClipboard(code ? code.textContent : pre.textContent, btn);
    };
    pre.appendChild(btn);
  });
}

// Run on DOM ready
document.addEventListener('DOMContentLoaded', addCopyButtons);
