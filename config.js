// KR and Leading Indicator targets, baselines, and labels
// YoY targets need baselines from your 2025 data — update baseline values when available

const KR_TARGETS = {
  KR1: {
    label: 'Workshop Attendees',
    field: 'KR1_Workshop_Attendees',
    baseline: null,          // Pull from MS Teams — update when known
    target: null,            // +50% YoY — computed once baseline is set
    targetDisplay: '+50% YoY',
    targetType: 'yoy',
    unit: '',
    source: 'MS Teams',
  },
  KR2: {
    label: 'LinkedIn Monthly Impressions',
    field: 'KR2_LinkedIn_Impressions',
    baseline: 5486,
    target: 25000,
    targetDisplay: '25,000/mo',
    targetType: 'absolute',
    unit: '',
    source: 'LinkedIn',
  },
  KR3: {
    label: 'Website Visitors',
    field: 'KR3_Website_Visitors',
    baseline: null,
    target: null,            // +60% YoY — computed once baseline is set
    targetDisplay: '+60% YoY',
    targetType: 'yoy',
    unit: '',
    source: 'GA4',
  },
  KR4: {
    label: 'LLM / AI Search Visibility',
    field: 'KR4_LLM_Platforms',
    baseline: 0,
    target: 3,
    targetDisplay: '3 platforms',
    targetType: 'absolute',
    unit: ' platforms',
    source: 'Manual',
  },
  KR5: {
    label: 'Media Mentions',
    field: 'KR5_Media_Mentions',
    baseline: 0,
    target: 20,
    targetDisplay: '20 YTD',
    targetType: 'ytd',
    unit: '',
    source: 'Manual',
  },
  KR6: {
    label: 'Employer Brand / Applications',
    field: 'KR6_Employer_Applications',
    baseline: null,
    target: null,            // +60% YoY — computed once baseline is set
    targetDisplay: '+60% YoY',
    targetType: 'yoy',
    unit: '',
    source: 'ATS',
  },
  KR7: {
    label: 'Offline Audience Reach',
    field: 'KR7_Offline_Reach',
    baseline: 0,
    target: 1000,
    targetDisplay: '1,000 YTD',
    targetType: 'ytd',
    unit: ' people',
    source: 'Manual',
  },
};

const L_TARGETS = {
  L1: { label: 'LinkedIn posts published',            field: 'L1_Posts_Published',          target: 2,        unit: '' },
  L2: { label: 'LinkedIn post avg impressions',       field: 'L2_Post_Avg_Impressions',     target: null,     unit: '' },
  L3: { label: 'Workshop invites / promo posts sent', field: 'L3_Workshop_Invites',         target: 1,        unit: '' },
  L4: { label: 'Active partner conversations (I6)',   field: 'L4_Partner_Conversations',    target: 2,        unit: '' },
  L5: { label: 'Case studies in approval pipeline',  field: 'L5_Case_Studies_Pipeline',    target: 1,        unit: '' },
  L6: { label: 'Media pitches sent',                 field: 'L6_Media_Pitches',            target: 1,        unit: '' },
  L7: { label: 'Speaking proposals submitted (I3)',   field: 'L7_Speaking_Proposals',       target: '1/mo',   unit: '' },
};

// Status thresholds
const STATUS = {
  ON_TRACK: { emoji: '✅', label: 'On Track', minPct: 80 },
  AT_RISK:  { emoji: '⚠️', label: 'At Risk',  minPct: 40 },
  BEHIND:   { emoji: '🔴', label: 'Behind',   minPct: 0  },
};

module.exports = { KR_TARGETS, L_TARGETS, STATUS };
