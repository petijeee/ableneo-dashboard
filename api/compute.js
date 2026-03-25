const { KR_TARGETS, L_TARGETS, STATUS } = require('../config');

/**
 * Calculate % to target for a given KR
 * Returns 0-100+ (can exceed 100 if above target)
 */
function calcPercentToTarget(value, krKey, allWeeks) {
  if (value == null) return null;
  const kr = KR_TARGETS[krKey];
  if (!kr) return null;

  if (kr.targetType === 'absolute') {
    if (!kr.target) return null;
    return Math.round((value / kr.target) * 100);
  }

  if (kr.targetType === 'ytd') {
    // value = cumulative YTD total vs annual target
    if (!kr.target) return null;
    return Math.round((value / kr.target) * 100);
  }

  if (kr.targetType === 'yoy') {
    // Need baseline — can't compute without it
    if (!kr.baseline || !kr.target) return null;
    return Math.round((value / kr.target) * 100);
  }

  return null;
}

/**
 * Map % to status emoji + label
 */
function calcStatus(pct) {
  if (pct == null) return { emoji: '—', label: 'No data' };
  if (pct >= STATUS.ON_TRACK.minPct) return STATUS.ON_TRACK;
  if (pct >= STATUS.AT_RISK.minPct)  return STATUS.AT_RISK;
  return STATUS.BEHIND;
}

/**
 * Compare two values and return trend arrow
 * threshold: 10% change = trend change
 */
function calcTrend(current, previous, threshold = 0.1) {
  if (current == null || previous == null || previous === 0) return '→';
  const change = (current - previous) / previous;
  if (change > threshold)  return '▲';
  if (change < -threshold) return '▼';
  return '→';
}

/**
 * Calculate 4-week moving average for a field across sorted weeks (newest last)
 */
function calc4WeekAvg(weeks, field) {
  const last4 = weeks.slice(-4);
  const values = last4.map(w => w[field]).filter(v => v != null);
  if (values.length === 0) return null;
  return Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10;
}

/**
 * Enrich all weeks with computed fields
 * weeks: array sorted ascending by date
 */
function enrichWeeks(weeks) {
  return weeks.map((week, i) => {
    const prev = i > 0 ? weeks[i - 1] : null;
    const enriched = { ...week };

    // Enrich KRs
    for (const krKey of Object.keys(KR_TARGETS)) {
      const field = KR_TARGETS[krKey].field;
      const value = week[field];
      const prevValue = prev ? prev[field] : null;
      const pct = calcPercentToTarget(value, krKey, weeks.slice(0, i + 1));
      const status = calcStatus(pct);
      const trend = calcTrend(value, prevValue);
      const avg4 = calc4WeekAvg(weeks.slice(0, i + 1), field);

      enriched[`${krKey}_pct`] = pct;
      enriched[`${krKey}_status`] = status.emoji;
      enriched[`${krKey}_statusLabel`] = status.label;
      enriched[`${krKey}_trend`] = trend;
      enriched[`${krKey}_avg4`] = avg4;
    }

    // Enrich Leading Indicators
    for (const lKey of Object.keys(L_TARGETS)) {
      const field = L_TARGETS[lKey].field;
      const value = week[field];
      const prevValue = prev ? prev[field] : null;
      const target = L_TARGETS[lKey].target;
      const avg4 = calc4WeekAvg(weeks.slice(0, i + 1), field);
      const trend = calcTrend(value, prevValue);

      let pct = null;
      if (value != null && target != null && typeof target === 'number') {
        pct = Math.round((value / target) * 100);
      }

      enriched[`${lKey}_pct`] = pct;
      enriched[`${lKey}_trend`] = trend;
      enriched[`${lKey}_avg4`] = avg4;
    }

    return enriched;
  });
}

/**
 * Generate week label from a date string
 * e.g. "2026-03-10" → "W11 · 9.3–13.3"
 */
function weekLabel(dateStr) {
  const d = new Date(dateStr);
  // Find Monday of that week
  const day = d.getDay(); // 0=Sun
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((day + 6) % 7));
  const friday = new Date(monday);
  friday.setDate(monday.getDate() + 4);

  const weekNum = getISOWeek(monday);
  const fmt = (dt) => `${dt.getDate()}.${dt.getMonth() + 1}`;
  return `W${weekNum} · ${fmt(monday)}–${fmt(friday)}`;
}

function getISOWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

/**
 * Get the Monday date of current week in YYYY-MM-DD format
 */
function currentWeekMonday() {
  const now = new Date();
  const day = now.getDay();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((day + 6) % 7));
  return monday.toISOString().slice(0, 10);
}

/**
 * Aggregate weekly data into monthly totals
 * KR1, KR2, KR3, KR6: SUM per month
 * KR4: LAST value of month (state metric — count of platforms)
 * KR5: YTD running total (cumulative across months)
 * L fields: SUM per month
 */
function aggregateByMonth(weeks) {
  if (!weeks.length) return [];

  const KR_AGG = {
    KR1: 'sum', KR2: 'sum', KR3: 'sum',
    KR4: 'last', KR5: 'ytd', KR6: 'sum',
  };

  // Group by YYYY-MM preserving insertion order
  const monthMap = new Map();
  weeks.forEach(week => {
    const d = new Date(week.week_start);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (!monthMap.has(key)) monthMap.set(key, []);
    monthMap.get(key).push(week);
  });

  let ytdAcc = {};
  const rawMonths = [];

  for (const [monthKey, mWeeks] of [...monthMap.entries()].sort()) {
    const [yr, mo] = monthKey.split('-').map(Number);
    const title = new Date(yr, mo - 1, 1)
      .toLocaleString('sk-SK', { month: 'long', year: 'numeric' });

    const m = { monthKey, title, week_start: `${monthKey}-01`, isMonthly: true };

    // Aggregate KR fields
    for (const [krKey, aggType] of Object.entries(KR_AGG)) {
      const kr = KR_TARGETS[krKey];
      if (!kr) continue;
      const vals = mWeeks.map(w => w[kr.field]).filter(v => v != null);
      if (!vals.length) { m[kr.field] = null; continue; }
      if (aggType === 'sum')       m[kr.field] = vals.reduce((a, b) => a + b, 0);
      else if (aggType === 'last') m[kr.field] = vals[vals.length - 1];
      else if (aggType === 'ytd') {
        ytdAcc[kr.field] = (ytdAcc[kr.field] || 0) + vals.reduce((a, b) => a + b, 0);
        m[kr.field] = ytdAcc[kr.field];
      }
    }

    // Aggregate L fields — sum per month
    for (const [, l] of Object.entries(L_TARGETS)) {
      const vals = mWeeks.map(w => w[l.field]).filter(v => v != null);
      m[l.field] = vals.length ? vals.reduce((a, b) => a + b, 0) : null;
    }

    rawMonths.push(m);
  }

  // Re-use enrichWeeks to compute pct / status / trend / avg4 for monthly data
  return enrichWeeks(rawMonths);
}

module.exports = { enrichWeeks, aggregateByMonth, calcPercentToTarget, calcStatus, calcTrend, calc4WeekAvg, weekLabel, currentWeekMonday };
