/**
 * admin.js - Admin Dashboard JavaScript
 */

// ── User management ──
async function changeUserRole(userId, select) {
  const role = select.value;
  const res = await apiPost(`/admin/users/${userId}/role`, { role });
  if (res.success) showToast(`Role updated to ${role}`, 'success');
  else { showToast(res.error || 'Failed', 'error'); select.value = select.value === 'admin' ? 'user' : 'admin'; }
}

async function toggleUserStatus(userId, btn) {
  const res = await apiPost(`/admin/users/${userId}/toggle-status`, {});
  if (res.success) {
    const isActive = res.is_active;
    btn.textContent = isActive ? 'Disable' : 'Enable';
    btn.className = isActive ? 'btn btn-sm btn-ghost' : 'btn btn-sm btn-success';
    const badge = document.getElementById(`status-badge-${userId}`);
    if (badge) {
      badge.textContent = isActive ? 'Active' : 'Disabled';
      badge.className = isActive ? 'badge badge-green' : 'badge badge-red';
    }
    showToast(isActive ? 'User enabled' : 'User disabled', 'success');
  } else showToast(res.error || 'Failed', 'error');
}

async function deleteUser(userId) {
  if (!confirm('Permanently delete this user and all their data?')) return;
  const res = await apiPost(`/admin/users/${userId}/delete`, {});
  if (res.success) { document.getElementById(`user-row-${userId}`)?.remove(); showToast('User deleted', 'success'); }
  else showToast(res.error || 'Failed', 'error');
}

async function deleteAdminFile(fileId) {
  if (!confirm('Delete this file?')) return;
  const res = await apiPost(`/admin/files/${fileId}/delete`, {});
  if (res.success) { document.getElementById(`file-row-${fileId}`)?.remove(); showToast('File deleted', 'success'); }
  else showToast(res.error || 'Failed', 'error');
}

async function deleteAdminChat(chatId) {
  if (!confirm('Delete this chat?')) return;
  const res = await apiPost(`/admin/chats/${chatId}/delete`, {});
  if (res.success) { document.getElementById(`chat-row-${chatId}`)?.remove(); showToast('Chat deleted', 'success'); }
  else showToast(res.error || 'Failed', 'error');
}

// ── API Key Management ──
async function saveGroqKey() {
  const key = document.getElementById('new-api-key')?.value.trim();
  if (!key) { showToast('Please enter an API key', 'warning'); return; }

  const btn = document.getElementById('save-key-btn');
  btn.disabled = true; btn.textContent = 'Saving...';
  const res = await apiPost('/admin/api-settings/update-groq-key', { api_key: key });
  btn.disabled = false; btn.textContent = 'Save API Key';

  if (res.success) {
    const maskedEl = document.getElementById('masked-key');
    if (maskedEl) maskedEl.textContent = res.masked;
    document.getElementById('new-api-key').value = '';
    showToast('API key saved securely', 'success');
    hideModal('confirm-key-modal');
  } else showToast(res.error || 'Failed to save key', 'error');
}

async function testGroqKey() {
  const key = document.getElementById('new-api-key')?.value.trim() || '';
  const btn = document.getElementById('test-key-btn');
  btn.disabled = true; btn.textContent = 'Testing...';

  const res = await apiPost('/admin/api-settings/test-groq-key', { api_key: key });
  btn.disabled = false; btn.textContent = 'Test Key';

  const resultEl = document.getElementById('test-result');
  if (resultEl) {
    const cls = res.status === 'active' ? 'alert-success' : 'alert-error';
    resultEl.className = `alert ${cls}`;
    resultEl.textContent = res.message;
    resultEl.style.display = 'block';
  }
}

document.getElementById('save-key-btn')?.addEventListener('click', () => showModal('confirm-key-modal'));
document.getElementById('confirm-save-key')?.addEventListener('click', saveGroqKey);
document.getElementById('test-key-btn')?.addEventListener('click', testGroqKey);

// ── Analytics Charts ──
function renderAdminCharts(signupData, fileTypeData, apiData) {
  // Signup trend
  const signupCtx = document.getElementById('signup-chart');
  if (signupCtx && signupData) {
    new Chart(signupCtx, {
      type: 'line',
      data: {
        labels: signupData.map(d => d[0]),
        datasets: [{ label: 'New Users', data: signupData.map(d => d[1]),
          borderColor: '#7C3AED', backgroundColor: 'rgba(124,58,237,0.1)',
          fill: true, tension: 0.4, borderWidth: 2 }]
      },
      options: { responsive: true, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                  x: { grid: { display: false } } } }
    });
  }

  // File types pie
  const fileCtx = document.getElementById('filetype-chart');
  if (fileCtx && fileTypeData) {
    const colors = ['#7C3AED','#A78BFA','#DDD6FE','#DBEAFE','#FCE7F3','#34D399','#F59E0B'];
    new Chart(fileCtx, {
      type: 'doughnut',
      data: {
        labels: fileTypeData.map(d => d[0].toUpperCase()),
        datasets: [{ data: fileTypeData.map(d => d[1]), backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }]
      },
      options: { responsive: true, plugins: { legend: { position: 'right' } } }
    });
  }

  // API usage
  const apiCtx = document.getElementById('api-chart');
  if (apiCtx && apiData) {
    new Chart(apiCtx, {
      type: 'bar',
      data: {
        labels: apiData.map(d => d[0]),
        datasets: [{ label: 'API Calls', data: apiData.map(d => d[1]),
          backgroundColor: 'rgba(124,58,237,0.6)', borderRadius: 6 }]
      },
      options: { responsive: true, plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                  x: { grid: { display: false } } } }
    });
  }
}
