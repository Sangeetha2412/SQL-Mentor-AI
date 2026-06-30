/**
 * data-explorer.js - Data Explorer page logic
 */

let currentPage = 1;
let currentSort = '';
let currentSortDir = 'asc';
let searchTimer = null;
const fileId = window.FILE_ID;

async function loadTableData() {
  const search = document.getElementById('search-input')?.value || '';
  const url = `/api/file-preview/${fileId}?page=${currentPage}&search=${encodeURIComponent(search)}&sort=${currentSort}&dir=${currentSortDir}`;
  const res = await fetch(url);
  const data = await res.json();
  if (data.error) { showToast(data.error, 'error'); return; }
  renderTable(data);
}

function renderTable(data) {
  const thead = document.getElementById('data-thead');
  const tbody = document.getElementById('data-tbody');
  if (!thead || !tbody) return;

  thead.innerHTML = '<tr>' + (data.columns || []).map(col => `
    <th onclick="sortBy('${col}')" title="Sort by ${col}">
      ${col}
      ${currentSort === col ? (currentSortDir === 'asc' ? ' ↑' : ' ↓') : ''}
    </th>`).join('') + '</tr>';

  tbody.innerHTML = (data.rows || []).map(row =>
    '<tr>' + (data.columns || []).map(col =>
      `<td title="${escRow(String(row[col] ?? ''))}">${escRow(String(row[col] ?? ''))}</td>`
    ).join('') + '</tr>'
  ).join('') || '<tr><td colspan="100" style="text-align:center;color:#6B5B85;padding:24px">No data found</td></tr>';

  // Pagination
  renderPagination(data.page, data.total_pages, data.filtered_total);

  // Row count
  const rc = document.getElementById('row-count');
  if (rc) rc.textContent = `Showing ${(data.page-1)*data.per_page+1}–${Math.min(data.page*data.per_page, data.filtered_total)} of ${data.filtered_total} rows`;
}

function renderPagination(page, total, filteredTotal) {
  const el = document.getElementById('pagination');
  if (!el || total <= 1) { if(el) el.innerHTML = ''; return; }
  let html = `<button class="page-btn" onclick="goPage(${page-1})" ${page<=1?'disabled':''}>‹ Prev</button>`;
  const start = Math.max(1, page-2), end = Math.min(total, page+2);
  if (start > 1) html += `<button class="page-btn" onclick="goPage(1)">1</button>${start>2?'<span style="padding:0 4px">…</span>':''}`;
  for (let i=start; i<=end; i++) html += `<button class="page-btn ${i===page?'active':''}" onclick="goPage(${i})">${i}</button>`;
  if (end < total) html += `${end<total-1?'<span style="padding:0 4px">…</span>':''}<button class="page-btn" onclick="goPage(${total})">${total}</button>`;
  html += `<button class="page-btn" onclick="goPage(${page+1})" ${page>=total?'disabled':''}>Next ›</button>`;
  el.innerHTML = html;
}

function goPage(p) { currentPage = p; loadTableData(); }

function sortBy(col) {
  if (currentSort === col) currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
  else { currentSort = col; currentSortDir = 'asc'; }
  currentPage = 1;
  loadTableData();
}

document.getElementById('search-input')?.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { currentPage = 1; loadTableData(); }, 400);
});

// ── SQL Query Runner ──
document.getElementById('run-query-btn')?.addEventListener('click', async () => {
  const query = document.getElementById('sql-editor')?.value.trim();
  if (!query) return;
  const resultDiv = document.getElementById('query-result');
  const btn = document.getElementById('run-query-btn');
  btn.disabled = true; btn.textContent = 'Running...';
  try {
    const res = await fetch(`/api/run-safe-query/${fileId}`, {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({query})
    });
    const data = await res.json();
    if (data.success) {
      let html = `<div class="query-result-header"><span>✅ ${data.row_count} rows returned${data.limited?' (limited to '+data.max_rows+'':''}</span></div>`;
      html += '<div class="table-wrapper"><table class="data-table"><thead><tr>' + data.columns.map(c=>`<th>${c}</th>`).join('') + '</tr></thead><tbody>';
      html += data.rows.map(row => '<tr>' + row.map(v=>`<td>${escRow(String(v??''))}</td>`).join('') + '</tr>').join('');
      html += '</tbody></table></div>';
      if (resultDiv) resultDiv.innerHTML = html;
    } else {
      if (resultDiv) resultDiv.innerHTML = `<div class="alert alert-error"><i class="fa-solid fa-triangle-exclamation"></i>${data.error}</div>`;
    }
  } catch(e) {
    if (resultDiv) resultDiv.innerHTML = `<div class="alert alert-error">Request failed: ${e.message}</div>`;
  }
  btn.disabled = false; btn.textContent = '▶ Run Query';
});

// ── Table click in schema sidebar ──
document.querySelectorAll('.schema-table-item[data-table]').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.schema-table-item').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
    const tbl = el.dataset.table;
    const editor = document.getElementById('sql-editor');
    if (editor) editor.value = `SELECT * FROM "${tbl}" LIMIT 50`;
  });
});

function escRow(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Download CSV ──
document.getElementById('download-csv-btn')?.addEventListener('click', async () => {
  const search = document.getElementById('search-input')?.value || '';
  const res = await fetch(`/api/file-preview/${fileId}?page=1&per_page=10000&search=${encodeURIComponent(search)}&sort=${currentSort}&dir=${currentSortDir}`);
  const data = await res.json();
  if (!data.columns) return;
  const rows = [data.columns, ...data.rows.map(r => data.columns.map(c => r[c] ?? ''))];
  const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `export_${fileId}.csv`;
  a.click();
});

// ── Init ──
if (fileId) loadTableData();
