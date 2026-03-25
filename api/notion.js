const { Client } = require('@notionhq/client');
const { KR_TARGETS, L_TARGETS } = require('../config');

let notion;
function getClient() {
  if (!notion) {
    notion = new Client({ auth: process.env.NOTION_TOKEN });
  }
  return notion;
}

const DB_ID = () => process.env.NOTION_DB_ID;

/**
 * Map a Notion page row to a flat JS object
 */
function rowToWeek(page) {
  const props = page.properties;
  const get = (key) => {
    const p = props[key];
    if (!p) return null;
    if (p.type === 'number') return p.number;
    if (p.type === 'rich_text') return p.rich_text.map(r => r.plain_text).join('');
    if (p.type === 'date') return p.date?.start ?? null;
    if (p.type === 'title') return p.title.map(r => r.plain_text).join('');
    return null;
  };

  const week = {
    id: page.id,
    title: get('Title'),
    week_start: get('Week'),
  };

  for (const cfg of Object.values(KR_TARGETS)) {
    week[cfg.field] = get(cfg.field);
  }
  for (const cfg of Object.values(L_TARGETS)) {
    week[cfg.field] = get(cfg.field);
  }

  week.Priority1 = get('Priority1');
  week.Priority2 = get('Priority2');
  week.Priority3 = get('Priority3');
  week.Notes     = get('Notes');

  return week;
}

/**
 * Fetch all weekly entries from the Notion DB, sorted ascending by week_start
 */
async function getAllWeeks() {
  const client = getClient();
  const results = [];
  let cursor;

  do {
    const res = await client.databases.query({
      database_id: DB_ID(),
      sorts: [{ property: 'Week', direction: 'ascending' }],
      start_cursor: cursor,
    });
    results.push(...res.results);
    cursor = res.has_more ? res.next_cursor : undefined;
  } while (cursor);

  return results.map(rowToWeek);
}

/**
 * Create a new weekly entry in the Notion DB
 * weekData: { week_start: 'YYYY-MM-DD', title: '...', KR1_Workshop_Attendees: null, ... }
 */
async function createWeek(weekData) {
  const client = getClient();
  const properties = {
    Title: {
      title: [{ text: { content: weekData.title || '' } }],
    },
    Week: {
      date: { start: weekData.week_start },
    },
  };

  const numFields = [
    ...Object.values(KR_TARGETS).map(c => c.field),
    ...Object.values(L_TARGETS).map(c => c.field),
  ];

  for (const field of numFields) {
    const val = weekData[field];
    properties[field] = { number: val != null ? val : null };
  }

  for (const textField of ['Priority1', 'Priority2', 'Priority3', 'Notes']) {
    const val = weekData[textField] || '';
    properties[textField] = { rich_text: [{ text: { content: val } }] };
  }

  const page = await client.pages.create({
    parent: { database_id: DB_ID() },
    properties,
  });

  return rowToWeek(page);
}

/**
 * Update specific fields of an existing weekly entry
 */
async function updateWeek(pageId, updates) {
  const client = getClient();
  const properties = {};

  for (const [key, value] of Object.entries(updates)) {
    if (key === 'Title') {
      properties.Title = { title: [{ text: { content: value } }] };
    } else if (key === 'Week') {
      properties.Week = { date: { start: value } };
    } else if (['Priority1', 'Priority2', 'Priority3', 'Notes'].includes(key)) {
      properties[key] = { rich_text: [{ text: { content: value || '' } }] };
    } else {
      properties[key] = { number: value != null ? value : null };
    }
  }

  const page = await client.pages.update({ page_id: pageId, properties });
  return rowToWeek(page);
}

module.exports = { getAllWeeks, createWeek, updateWeek };
