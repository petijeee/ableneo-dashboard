// ─── State ──────────────────────────────────────────────────────
let allWeeks  = [];
let allMonths = [];
let config = { KR_TARGETS: {}, L_TARGETS: {} };
let selectedWeekIdx  = -1;
let selectedMonthIdx = -1;
let viewMode = 'weekly'; // 'weekly' | 'monthly'
let trendCharts = {};

// ─── Init ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadData();
    setupEventListeners();
  } catch (err) {
    showError(err.message);
  }
});

async function loadData() {
  showLoading(true);

  const [dataRes, configRes, monthlyRes] = await Promise.all([
    fetch('/api/data').then(r => r.json()),
    fetch('/api/config').then(r => r.json()),
    fetch('/api/monthly').then(r => r.json()),
  ]);

  if (!dataRes.ok)   throw new Error(dataRes.error   || 'Failed to load data');
  if (!configRes.ok) throw new Error(configRes.error || 'Failed to load config');

  allWeeks  = dataRes.weeks;
  allMonths = monthlyRes.ok ? (monthlyRes.months || []) : [];
  config    = { KR_TARGETS: configRes.KR_TARGETS, L_TARGETS: configRes.L_TARGETS };

  showLoading(false);
  buildWeekSelector();
  buildMonthSelector();

  if (viewMode === 'monthly') {
    selectMonth(allMonths.length - 1);
  } else {
    selectWeek(allWeeks.length - 1);
  }
}

// ─── View Toggle ─────────────────────────────────────────────────
function switchView(mode) {
  viewMode = mode;

  const weekSel  = document.getElementById('week-selector');
  const monthSel = document.getElementById('month-selector');
  const btnW     = document.getElementById('btn-view-weekly');
  const btnM     = document.getElementById('btn-view-monthly');
  const liHdr    = document.getElementById('li-period-header');
  const liPrev   = document.getElementById('li-prev-header');
  const trendTtl = document.getElementById('trend-section-title');

  if (mode === 'weekly') {
    weekSel.style.display  = '';
    monthSel.style.display = 'none';
    btnW.classList.add('toggle-active');
    btnM.classList.remove('toggle-active');
    if (liHdr)    liHdr.textContent    = 'Tento týždeň';
    if (liPrev)   liPrev.textContent   = 'Min. týždeň';
    if (trendTtl) trendTtl.textContent = 'Trendy — posledné týždne';
    selectWeek(selectedWeekIdx >= 0 ? selectedWeekIdx : allWeeks.length - 1);
  } else {
    weekSel.style.display  = 'none';
    monthSel.style.display = '';
    btnW.classList.remove('toggle-active');
    btnM.classList.add('toggle-active');
    if (liHdr)    liHdr.textContent    = 'Tento mesiac';
    if (liPrev)   liPrev.textContent   = 'Min. mesiac';
    if (trendTtl) trendTtl.textContent = 'Trendy — posledné mesiace';
    selectMonth(selectedMonthIdx >= 0 ? selectedMonthIdx : allMonths.length - 1);
  }
}

// ─── Week Selector ───────────────────────────────────────────────
function buildWeekSelector() {
  const sel = document.getElementById('week-selector');
  sel.innerHTML = '';

  if (allWeeks.length === 0) {
    const opt = document.createElement('option');
    opt.textContent = 'Žiadne dáta — vytvor prvý týždeň';
    sel.appendChild(opt);
    return;
  }

  allWeeks.forEach((w, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = w.title || w.week_start || `Týždeň ${i + 1}`;
    sel.appendChild(opt);
  });
  sel.value = allWeeks.length - 1;
}

// ─── Month Selector ──────────────────────────────────────────────
function buildMonthSelector() {
  const sel = document.getElementById('month-selector');
  sel.innerHTML = '';

  if (allMonths.length === 0) {
    const opt = document.createElement('option');
    opt.textContent = 'Žiadne mesačné dáta';
    sel.appendChild(opt);
    return;
  }

  allMonths.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = m.title || m.monthKey || `Mesiac ${i + 1}`;
    sel.appendChild(opt);
  });
  sel.value = allMonths.length - 1;
}

function selectWeek(idx) {
  if (allWeeks.length === 0) return;
  selectedWeekIdx = idx;
  const week = allWeeks[idx];

  document.getElementById('week-selector').value = idx;
  document.getElementById('subtitle-week').textContent = week.title || week.week_start || '';

  renderKRGrid(week);
  renderCharts(allWeeks, selectedWeekIdx);
  renderLeadingIndicators(week, idx, allWeeks);
  renderPriorities(week);
  renderNotes(week);
  showWeeklyOnly(true);
  document.getElementById('main-content').style.display = '';
}

function selectMonth(idx) {
  if (allMonths.length === 0) return;
  selectedMonthIdx = idx;
  const month = allMonths[idx];

  document.getElementById('month-selector').value = idx;
  document.getElementById('subtitle-week').textContent = month.title || month.monthKey || '';

  renderKRGrid(month);
  renderCharts(allMonths, selectedMonthIdx);
  renderLeadingIndicators(month, idx, allMonths);
  showWeeklyOnly(false);
  document.getElementById('main-content').style.display = '';
}

function showWeeklyOnly(show) {
  document.querySelectorAll('.weekly-only').forEach(el => {
    el.style.display = show ? '' : 'none';
  });
}

// ─── KR Grid ─────────────────────────────────────────────────────
function renderKRGrid(data) {
  const grid = document.getElementById('kr-grid');
  grid.innerHTML = '';
  Object.keys(config.KR_TARGETS).forEach(krKey => {
    const kr       = config.KR_TARGETS[krKey];
    const value    = data[kr.field];
    const yoyValue = kr.yoyField ? data[kr.yoyField] : null;
    const pct      = data[`${krKey}_pct`];
    const status   = data[`${krKey}_status`] || '—';
    grid.appendChild(buildKRCard({ krKey, kr, value, yoyValue, pct, status, isMonthly: !!data.isMonthly }));
  });
}

function buildKRCard({ krKey, kr, value, yoyValue, pct, status, isMonthly }) {
  const card = document.createElement('div');
  card.className = 'kr-card';

  const fillClass  = pct == null ? 'fill-gray' : pct >= 80 ? 'fill-green' : pct >= 40 ? 'fill-yellow' : 'fill-red';
  const fillWidth  = pct == null ? 0 : Math.min(pct, 100);

  const valueHtml  = value != null
    ? `<div class="kr-value">${fmt(value)}${kr.unit || ''}</div>`
    : `<div class="kr-value-nodata">—</div>`;

  // YoY badge — shown when yoyField is defined and has data
  const yoyHtml = yoyValue != null
    ? (() => {
        const pctNum    = Math.round(yoyValue * 100);
        const sign      = pctNum >= 0 ? '+' : '';
        const yoyTarget = kr.yoyTarget || null;
        let color, indicator;
        if (yoyTarget != null) {
          if (pctNum >= yoyTarget)               { color = '#b6ff5e'; indicator = '✅'; }
          else if (pctNum >= yoyTarget * 0.5)    { color = '#ffd166'; indicator = '⚠️'; }
          else                                    { color = '#ff6b6b'; indicator = '🔴'; }
        } else {
          color = pctNum >= 0 ? '#b6ff5e' : '#ff6b6b';
          indicator = '';
        }
        return `<div class="kr-yoy-badge" style="color:${color}">${indicator} ${sign}${pctNum}% YoY</div>`;
      })()
    : '';

  const targetHtml = kr.targetDisplay
    ? `<div class="kr-target">Target: ${kr.targetDisplay}</div>`
    : '';

  const pctHtml = pct != null
    ? `<div class="kr-pct">${pct}% of target</div>`
    : `<div class="kr-pct" style="color:var(--text-muted)">Vyplniť hodnotu</div>`;

  card.innerHTML = `
    <div class="kr-card-header">
      <div class="kr-label">${krKey} · ${kr.label}</div>
      <div class="kr-status">${status}</div>
    </div>
    ${valueHtml}
    ${yoyHtml}
    ${targetHtml}
    <div class="kr-progress-bar">
      <div class="kr-progress-fill ${fillClass}" style="width:${fillWidth}%"></div>
    </div>
    ${pctHtml}
    <div class="kr-source-badge">${kr.source || ''}</div>
  `;
  return card;
}

// ─── Trend Charts ─────────────────────────────────────────────────
function renderCharts(dataArr, selectedIdx) {
  const grid = document.getElementById('trend-grid');
  Object.values(trendCharts).forEach(c => c.destroy());
  trendCharts = {};
  grid.innerHTML = '';

  Object.keys(config.KR_TARGETS).forEach(krKey => {
    const kr     = config.KR_TARGETS[krKey];
    const labels = dataArr.map(d => d.title || d.week_start || '');
    const values = dataArr.map(d => d[kr.field]);
    if (values.every(v => v == null)) return;

    const card = document.createElement('div');
    card.className = 'trend-card';
    const canvasId = `chart-${krKey}`;
    card.innerHTML = `
      <div class="trend-card-title">${krKey} · ${kr.label}</div>
      <div class="trend-canvas-wrapper"><canvas id="${canvasId}"></canvas></div>
    `;
    grid.appendChild(card);

    const ctx = card.querySelector(`#${canvasId}`).getContext('2d');
    trendCharts[krKey] = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: '#cdde00',
          backgroundColor: 'rgba(205,222,0,.07)',
          pointBackgroundColor: values.map((v, i) => i === selectedIdx ? '#b6b0f2' : '#cdde00'),
          pointRadius: values.map((v, i) => i === selectedIdx ? 5 : 3),
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          spanGaps: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `${fmt(ctx.raw)}${kr.unit || ''}` } },
        },
        scales: {
          x: {
            display: true,
            ticks: { color: '#49576a', font: { size: 10, family: 'Poppins' }, maxRotation: 0, maxTicksLimit: 6 },
            grid: { color: '#313840' },
          },
          y: {
            display: true,
            ticks: { color: '#49576a', font: { size: 10, family: 'Poppins' } },
            grid: { color: '#313840' },
          },
        },
      },
    });
  });

  if (grid.children.length === 0) {
    grid.innerHTML = '<p style="color:var(--text-muted);font-size:13px">Zatiaľ žiadne dáta na zobrazenie trendov. Vyplň hodnoty v Notion.</p>';
  }
}

// ─── Leading Indicators ───────────────────────────────────────────
function renderLeadingIndicators(data, idx, dataArr) {
  const tbody = document.getElementById('li-tbody');
  tbody.innerHTML = '';
  const prev  = idx > 0 ? dataArr[idx - 1] : null;

  Object.keys(config.L_TARGETS).forEach(lKey => {
    const l          = config.L_TARGETS[lKey];
    const value      = data[l.field];
    const prevValue  = prev ? prev[l.field] : null;
    const avg4       = data[`${lKey}_avg4`];
    const trend      = data[`${lKey}_trend`] || '→';
    const target     = l.target;
    const pct        = data[`${lKey}_pct`];
    const trendClass = trend === '▲' ? 'trend-up' : trend === '▼' ? 'trend-down' : 'trend-flat';

    let targetCell = '';
    if (target == null) {
      targetCell = `<span class="target-nodata">—</span>`;
    } else if (value != null && typeof target === 'number') {
      targetCell = value >= target
        ? `<span class="target-hit">${target} ✓</span>`
        : `<span class="target-miss">${target}</span>`;
    } else {
      targetCell = `<span class="target-nodata">${target}</span>`;
    }

    let valueCell = '';
    if (value != null && pct != null && typeof target === 'number') {
      const bw = Math.min(pct, 100);
      const bc = pct >= 100 ? 'fill-green' : pct >= 50 ? 'fill-yellow' : 'fill-red';
      valueCell = `
        <div class="li-mini-progress">
          <span class="li-val">${value}</span>
          <div class="li-mini-bar"><div class="li-mini-fill ${bc}" style="width:${bw}%"></div></div>
        </div>`;
    } else {
      valueCell = value != null
        ? `<span class="li-val">${value}</span>`
        : `<span class="li-val-null">—</span>`;
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="li-key">${lKey}</td>
      <td style="font-size:12px;color:var(--text-muted);max-width:220px">${l.label}</td>
      <td>${valueCell}</td>
      <td>${prevValue != null ? prevValue : '<span class="li-val-null">—</span>'}</td>
      <td>${avg4 != null ? avg4 : '<span class="li-val-null">—</span>'}</td>
      <td class="${trendClass}">${trend}</td>
      <td>${targetCell}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ─── Priorities + Notes ───────────────────────────────────────────
function renderPriorities(week) {
  const container = document.getElementById('priorities');
  container.innerHTML = '';
  ['Priority1', 'Priority2', 'Priority3'].forEach((key, i) => {
    const text = week[key];
    const div  = document.createElement('div');
    div.className = 'priority-item';
    div.innerHTML = `
      <span class="priority-num">#${i + 1}</span>
      <span class="${text ? 'priority-text' : 'priority-empty'}">${text || 'Nevyplnené'}</span>
    `;
    container.appendChild(div);
  });
}

function renderNotes(week) {
  const box = document.getElementById('notes');
  if (week.Notes) {
    box.textContent = week.Notes;
    box.classList.remove('notes-empty');
  } else {
    box.innerHTML = '<em class="notes-empty">Žiadne poznámky</em>';
  }
}

// ─── Event Listeners ─────────────────────────────────────────────
function setupEventListeners() {
  document.getElementById('week-selector').addEventListener('change', e => {
    selectWeek(parseInt(e.target.value, 10));
  });

  document.getElementById('month-selector').addEventListener('change', e => {
    selectMonth(parseInt(e.target.value, 10));
  });

  document.getElementById('btn-view-weekly').addEventListener('click',  () => switchView('weekly'));
  document.getElementById('btn-view-monthly').addEventListener('click', () => switchView('monthly'));

  document.getElementById('btn-new-week').addEventListener('click', () => {
    const lastWeek  = allWeeks[allWeeks.length - 1];
    let defaultDate = currentWeekMonday();
    if (lastWeek?.week_start) {
      const nextMon = new Date(lastWeek.week_start);
      nextMon.setDate(nextMon.getDate() + 7);
      if (nextMon <= new Date()) defaultDate = nextMon.toISOString().slice(0, 10);
    }
    document.getElementById('new-week-date').value = defaultDate;
    document.getElementById('modal-overlay').style.display = 'flex';
  });

  document.getElementById('modal-cancel').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });

  document.getElementById('modal-create').addEventListener('click', async () => {
    const dateInput = document.getElementById('new-week-date').value;
    if (!dateInput) { alert('Vyber dátum'); return; }

    const btn = document.getElementById('modal-create');
    btn.disabled = true;
    btn.textContent = 'Vytvára sa…';

    try {
      const res  = await fetch('/api/weeks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ week_start: dateInput }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error);
      closeModal();
      await loadData();
    } catch (err) {
      alert('Chyba: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Vytvoriť';
    }
  });
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

// ─── Helpers ─────────────────────────────────────────────────────
function showLoading(on) {
  document.getElementById('loading').style.display = on ? '' : 'none';
  document.getElementById('main-content').style.display = on ? 'none' : '';
}

function showError(msg) {
  document.getElementById('loading').style.display = 'none';
  const el = document.getElementById('error');
  el.style.display = '';
  el.textContent = '❌ ' + msg + '\n\nSkontroluj .env (NOTION_TOKEN, NOTION_DB_ID) a reštartuj server.';
}

function fmt(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('sk-SK');
}

function currentWeekMonday() {
  const now    = new Date();
  const day    = now.getDay();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((day + 6) % 7));
  return monday.toISOString().slice(0, 10);
}
