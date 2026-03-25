require('dotenv').config();
const express = require('express');
const path = require('path');
const { getAllWeeks, createWeek } = require('./api/notion');
const { enrichWeeks, aggregateByMonth, weekLabel, currentWeekMonday } = require('./api/compute');
const { KR_TARGETS, L_TARGETS } = require('./config');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// --- API routes ---

// GET /api/data — all weeks with computed fields
app.get('/api/data', async (req, res) => {
  try {
    const weeks = await getAllWeeks();
    const enriched = enrichWeeks(weeks);
    res.json({ ok: true, weeks: enriched });
  } catch (err) {
    console.error('GET /api/data error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /api/monthly — weekly data aggregated by month
app.get('/api/monthly', async (req, res) => {
  try {
    const weeks = await getAllWeeks();
    const months = aggregateByMonth(weeks);
    res.json({ ok: true, months });
  } catch (err) {
    console.error('GET /api/monthly error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /api/config — targets and labels for frontend
app.get('/api/config', (req, res) => {
  res.json({ ok: true, KR_TARGETS, L_TARGETS });
});

// POST /api/weeks — create a new weekly entry (called by scheduled task or "New Week" button)
app.post('/api/weeks', async (req, res) => {
  try {
    const weekStart = req.body.week_start || currentWeekMonday();
    const title = req.body.title || weekLabel(weekStart);

    const week = await createWeek({
      week_start: weekStart,
      title,
      ...req.body,
    });

    res.status(201).json({ ok: true, week });
  } catch (err) {
    console.error('POST /api/weeks error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    ok: true,
    notion_configured: !!(process.env.NOTION_TOKEN && process.env.NOTION_DB_ID),
    timestamp: new Date().toISOString(),
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Dashboard running → http://localhost:${PORT}`);
  if (!process.env.NOTION_TOKEN || !process.env.NOTION_DB_ID) {
    console.warn('⚠️  NOTION_TOKEN or NOTION_DB_ID not set — copy .env.example to .env and fill in values');
  }
});
