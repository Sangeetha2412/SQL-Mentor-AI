/**
 * charts.js - Visualization page logic
 */

let currentChart = null;
let currentChartConfig = null;
const fileId = window.FILE_ID;

// ── Chart type selection ──
document.querySelectorAll('.chart-type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
  });
});

// ── Generate Chart ──
document.getElementById('generate-chart-btn')?.addEventListener('click', async () => {
  const chartType = document.querySelector('.chart-type-btn.selected')?.dataset.type || 'bar';
  const xCol = document.getElementById('x-column')?.value;
  const yCol = document.getElementById('y-column')?.value;
  const agg = document.getElementById('aggregation')?.value || 'count';

  if (!xCol) { showToast('Please select an X-axis column', 'warning'); return; }

  const btn = document.getElementById('generate-chart-btn');
  btn.disabled = true; btn.textContent = '⏳ Generating...';

  try {
    const res = await fetch(`/api/generate-chart/${fileId}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ chart_type: chartType, x_column: xCol, y_column: yCol, aggregation: agg })
    });
    const data = await res.json();

    if (data.error) { showToast(data.error, 'error'); return; }

    currentChartConfig = data.chart_config;
    renderChart(data.chart_config);

    const insightEl = document.getElementById('chart-insight');
    if (insightEl) {
      insightEl.innerHTML = window.marked ? marked.parse(data.insight || '') : (data.insight || '');
      insightEl.style.display = 'block';
    }

    document.getElementById('chart-actions')?.style.setProperty('display','flex');
  } catch(e) {
    showToast('Chart generation failed: ' + e.message, 'error');
  }

  btn.disabled = false; btn.textContent = '✨ Generate Chart';
});

function renderChart(config) {
  const canvas = document.getElementById('chart-canvas');
  if (!canvas) return;
  if (currentChart) { currentChart.destroy(); currentChart = null; }
  currentChart = new Chart(canvas, config);
}

// ── Save Chart ──
document.getElementById('save-chart-btn')?.addEventListener('click', async () => {
  if (!currentChartConfig) { showToast('Generate a chart first', 'warning'); return; }
  const title = prompt('Chart title:', 'My Chart');
  if (!title) return;

  const chartType = document.querySelector('.chart-type-btn.selected')?.dataset.type || 'bar';
  const res = await apiPost('/api/save-chart', {
    file_id: fileId, title, chart_type: chartType, chart_config: currentChartConfig
  });
  if (res.success) showToast('Chart saved!', 'success');
  else showToast('Failed to save chart', 'error');
});

// ── Download Chart PNG ──
document.getElementById('download-chart-btn')?.addEventListener('click', () => {
  const canvas = document.getElementById('chart-canvas');
  if (!canvas) return;
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = 'chart.png';
  a.click();
});

// ── Delete saved chart ──
async function deleteSavedChart(chartId) {
  if (!confirm('Delete this saved chart?')) return;
  const res = await apiPost(`/api/delete-chart/${chartId}`, {});
  if (res.success) {
    document.getElementById(`saved-chart-${chartId}`)?.remove();
    showToast('Chart deleted', 'success');
  }
}

// ── Load saved chart ──
async function loadSavedChart(chartId, configJson) {
  try {
    const config = JSON.parse(configJson);
    renderChart(config);
    currentChartConfig = config;
    showToast('Chart loaded', 'success');
  } catch(e) {
    showToast('Failed to load chart', 'error');
  }
}
