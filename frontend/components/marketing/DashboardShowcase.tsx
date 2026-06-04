'use client';

/**
 * Full-width product showcase section.
 *
 * Composition (paired with parent `.reveal` for scroll-triggered
 * animations on the trend chart):
 *
 *   ┌── browser chrome ─────────────────────────────────────────────┐
 *   │  KPI strip (4 cards)                                          │
 *   ├──────────────────────────────┬────────────────────────────────┤
 *   │  High-priority companies     │  AI Insight (live)             │
 *   │  table (6 rows)              │  60-day overdue trend (SVG)    │
 *   │                              │  Recent alerts (3)             │
 *   ├──────────────────────────────┴────────────────────────────────┤
 *   │  Sector × risk heatmap (compact grid)                         │
 *   └───────────────────────────────────────────────────────────────┘
 */

import {
  Building2,
  TrendingUp,
  TrendingDown,
  MessageSquare,
  Mail,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Activity,
} from 'lucide-react';

const ROWS = [
  { name: 'Thornbury Construction Ltd', crn: '09182734', sector: 'Construction (43.21)',           city: 'Vauxhall, SW9', risk: 'critical', score: 87, deadline: 'Overdue 14d' },
  { name: 'Camden Property Holdings',   crn: '11738490', sector: 'Letting of property (68.20)',    city: 'Camden, NW1',   risk: 'high',     score: 74, deadline: '5d' },
  { name: 'Pixel & Pine Studios',       crn: '13902187', sector: 'Computer services (62.09)',     city: 'Hackney, E2',   risk: 'medium',   score: 55, deadline: '21d' },
  { name: 'Mercer & Vale Consultants',  crn: '12384902', sector: 'Management consultancy (70.22)', city: 'City, EC2',     risk: 'high',     score: 71, deadline: '8d' },
  { name: 'Bow Lane Bakeries Ltd',      crn: '14029384', sector: 'Manufacture of bread (10.71)',   city: 'Bow, E14',      risk: 'medium',   score: 48, deadline: '17d' },
  { name: 'Highbury Care Group',        crn: '10398472', sector: 'Residential care (87.30)',      city: 'Highbury, N5',  risk: 'high',     score: 68, deadline: '6d' },
];

const RISK_STYLES: Record<string, string> = {
  critical: 'bg-risk-critical/10 text-risk-critical border-risk-critical/30',
  high:     'bg-risk-high/10 text-risk-high border-risk-high/30',
  medium:   'bg-risk-medium/10 text-risk-medium border-risk-medium/30',
  low:      'bg-risk-low/10 text-risk-low border-risk-low/30',
};

// 60-day overdue trend — slightly trending up with realistic noise
const TREND = [
  142, 138, 140, 145, 148, 152, 156, 153, 158, 162, 159, 164,
  168, 165, 171, 175, 178, 174, 180, 184, 181, 188, 192, 195,
  191, 198, 203, 199, 206, 210, 214, 211, 218, 223, 220, 227,
  231, 228, 234, 240, 238, 244, 249, 246, 252, 257, 263, 260,
  267, 272, 268, 275, 281, 285, 282, 289, 294, 298, 301, 304,
];

// Sectors × risk heatmap data (counts of companies in each bucket)
const SECTORS = ['Construction', 'Property', 'eCommerce', 'Care', 'Consultants', 'Hospitality'];
const LEVELS = ['Critical', 'High', 'Medium', 'Low'] as const;
const HEATMAP: Record<string, number[]> = {
  Construction: [42, 87, 124, 198],
  Property:     [28, 64, 142, 211],
  eCommerce:    [9,  31, 98,  176],
  Care:         [18, 47, 76,  112],
  Consultants:  [11, 38, 89,  154],
  Hospitality:  [22, 41, 67,  98],
};

export function DashboardShowcase() {
  return (
    <div className="relative">
      {/* Browser chrome */}
      <div className="bg-navy-900 rounded-t-md px-5 py-3 flex items-center gap-2 border-b border-navy-800">
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-risk-critical/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-risk-medium/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-risk-low/70" />
        </div>
        <div className="flex-1 mx-4 max-w-md bg-navy-800 rounded-sm px-3 py-1 text-[11px] text-cream-200/60 font-mono">
          radar.dennisandassociates.co.uk/companies
        </div>
        <span className="text-[10px] text-cream-200/40 uppercase tracking-wider2">live preview</span>
      </div>

      {/* Dashboard body */}
      <div className="bg-cream-50 border border-t-0 border-navy-200/60 rounded-b-md p-4 lg:p-6">
        {/* KPI strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-5">
          <Kpi label="Companies tracked"  value="4,423" tone="navy" />
          <Kpi label="High-value leads"   value="312"   tone="gold" delta="+18 this week" />
          <Kpi label="Overdue filings"    value="1,847" tone="risk" delta="+12.4% vs 7d" />
          <Kpi label="Alerts sent (24h)"  value="89"    tone="navy" />
        </div>

        {/* Main grid: table left, right-column stack */}
        <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4 lg:gap-5">
          {/* --- Companies table --- */}
          <div className="bg-white border border-navy-200/50 rounded-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-navy-200/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="w-3.5 h-3.5 text-navy-500" />
                <span className="eyebrow">High-priority companies</span>
              </div>
              <span className="text-[10px] text-navy-500">sorted by lead score</span>
            </div>
            <table className="w-full text-xs">
              <thead className="bg-navy-50/60">
                <tr className="text-[10px] uppercase tracking-wider2 text-navy-500">
                  <th className="text-left font-medium px-4 py-2">Company</th>
                  <th className="text-left font-medium px-4 py-2 hidden lg:table-cell">Sector</th>
                  <th className="text-left font-medium px-4 py-2">Risk</th>
                  <th className="text-left font-medium px-4 py-2">Score</th>
                  <th className="text-right font-medium px-4 py-2">Deadline</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-200/40">
                {ROWS.map((r) => (
                  <tr key={r.crn} className="hover:bg-cream-50/60 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-navy-900">{r.name}</div>
                      <div className="font-mono text-[10px] text-navy-500 mt-0.5">
                        {r.crn} · {r.city}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-navy-600 text-[11px] hidden lg:table-cell">
                      {r.sector}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`pill border ${RISK_STYLES[r.risk]} capitalize`}>
                        <span className="w-1 h-1 rounded-full bg-current" />
                        {r.risk}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <div className="font-mono tabular-nums text-navy-900 w-5">{r.score}</div>
                        <div className="flex-1 h-1 bg-navy-100 rounded-full overflow-hidden max-w-[60px]">
                          <div
                            className={`h-full ${
                              r.score >= 70 ? 'bg-risk-critical' :
                              r.score >= 50 ? 'bg-risk-high' :
                              r.score >= 30 ? 'bg-risk-medium' : 'bg-navy-400'
                            }`}
                            style={{ width: `${r.score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={
                        r.deadline.startsWith('Overdue') ? 'text-risk-critical font-medium' : 'text-navy-700'
                      }>
                        {r.deadline}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Right column: AI insight, trend chart, alerts */}
          <div className="space-y-4">
            <AIInsightCard />
            <OverdueTrendChart />
            <AlertsPanel />
          </div>
        </div>

        {/* Heatmap row */}
        <div className="mt-5">
          <RiskHeatmap />
        </div>
      </div>
    </div>
  );
}

// ============================================================
// AI INSIGHT CARD — looks like real LLM output
// ============================================================
function AIInsightCard() {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm p-4 relative overflow-hidden">
      {/* Accent rail */}
      <span className="absolute left-0 top-0 h-full w-0.5 bg-accent" />

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span className="eyebrow">AI insight · live</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="thinking-dot w-1 h-1 rounded-full bg-accent" />
          <span className="thinking-dot w-1 h-1 rounded-full bg-accent" />
          <span className="thinking-dot w-1 h-1 rounded-full bg-accent" />
        </div>
      </div>

      <div className="text-sm font-medium text-navy-900 mb-1">
        Thornbury Construction Ltd
      </div>
      <div className="font-mono text-[10px] text-navy-500 mb-3">
        CRN 09182734 · risk 87 · est. £4.8k ARR
      </div>

      <p className="text-[11px] text-navy-700 leading-relaxed">
        Three converging signals indicate a high-confidence outreach window:
      </p>
      <ul className="mt-2 space-y-1 text-[11px] text-navy-700">
        <li className="flex gap-2">
          <span className="text-accent shrink-0">·</span>
          Accounts overdue 14d — late filer in 3 of last 4 years
        </li>
        <li className="flex gap-2">
          <span className="text-accent shrink-0">·</span>
          CIS subcontractor scheme active since 2019
        </li>
        <li className="flex gap-2">
          <span className="text-accent shrink-0">·</span>
          Director appointed 6 weeks ago — possible restructure
        </li>
      </ul>

      <div className="mt-3 pt-3 border-t border-navy-200/40">
        <div className="text-[10px] uppercase tracking-wider2 text-navy-500 mb-1">Suggested approach</div>
        <p className="text-[11px] text-navy-700 leading-relaxed">
          Email finance director within 48h. Lead with CIS year-end remediation;
          secondary offer monthly bookkeeping.
        </p>
        <div className="mt-2 flex items-center justify-between text-[10px]">
          <span className="text-navy-500">Confidence</span>
          <span className="font-mono tabular-nums text-accent">0.87</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// OVERDUE TREND CHART — animated SVG line
// ============================================================
function OverdueTrendChart() {
  const max = Math.max(...TREND);
  const min = Math.min(...TREND);
  const range = max - min || 1;

  // viewBox 600 x 140; left padding 30 for y-axis labels, top 10, bottom 20
  const w = 600;
  const h = 140;
  const pad = { left: 30, right: 8, top: 10, bottom: 22 };
  const innerW = w - pad.left - pad.right;
  const innerH = h - pad.top - pad.bottom;

  const points = TREND.map((v, i) => {
    const x = pad.left + (i / (TREND.length - 1)) * innerW;
    const y = pad.top + (1 - (v - min) / range) * innerH;
    return [x, y] as const;
  });

  const pathD = points
    .map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`))
    .join(' ');

  const areaD =
    `${pathD} L ${points[points.length - 1][0]} ${h - pad.bottom} L ${pad.left} ${h - pad.bottom} Z`;

  const delta = ((TREND[TREND.length - 1] - TREND[0]) / TREND[0]) * 100;

  return (
    <div className="bg-white border border-navy-200/50 rounded-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-navy-500" />
          <span className="eyebrow">Overdue accounts · 60d</span>
        </div>
        <span
          className={`flex items-center gap-1 text-[10px] font-medium ${
            delta >= 0 ? 'text-risk-high' : 'text-risk-low'
          }`}
        >
          {delta >= 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
          {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
        </span>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto" preserveAspectRatio="none">
        <defs>
          <linearGradient id="trend-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#c89b3c" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#c89b3c" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Y gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((g) => {
          const y = pad.top + g * innerH;
          const label = Math.round(max - g * range);
          return (
            <g key={g}>
              <line
                x1={pad.left} x2={w - pad.right}
                y1={y} y2={y}
                stroke="#e8e1ce"
                strokeWidth="0.5"
                strokeDasharray={g === 0 || g === 1 ? '0' : '2 2'}
              />
              <text
                x={pad.left - 4} y={y + 3}
                textAnchor="end"
                fontSize="9"
                fill="#7a8197"
                fontFamily="'JetBrains Mono', monospace"
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* X labels */}
        {[0, 14, 28, 42, 59].map((day) => {
          const x = pad.left + (day / (TREND.length - 1)) * innerW;
          return (
            <text
              key={day}
              x={x} y={h - pad.bottom + 12}
              textAnchor="middle"
              fontSize="9"
              fill="#7a8197"
              fontFamily="'JetBrains Mono', monospace"
            >
              {day === 0 ? '60d ago' : day === 59 ? 'today' : `${59 - day}d`}
            </text>
          );
        })}

        {/* Area fill (delayed fade) */}
        <path d={areaD} fill="url(#trend-grad)" className="fade-fill" opacity="0" />

        {/* Trend line (animated draw) */}
        <path
          d={pathD}
          fill="none"
          stroke="#c89b3c"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="draw-line"
          pathLength="1"
        />

        {/* End-point dot */}
        <circle
          cx={points[points.length - 1][0]}
          cy={points[points.length - 1][1]}
          r="3"
          fill="#c89b3c"
          className="fade-fill"
          opacity="0"
        />
      </svg>
    </div>
  );
}

// ============================================================
// ALERTS PANEL
// ============================================================
function AlertsPanel() {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-navy-200/50 flex items-center gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-risk-high" />
        <span className="eyebrow">Recent alerts</span>
      </div>
      <div className="divide-y divide-navy-200/40">
        <AlertRow channel="slack" icon={MessageSquare} title="High-value lead"   meta="Camden Property · 4m ago" />
        <AlertRow channel="email" icon={Mail}          title="Overdue accounts"  meta="Thornbury Co · 18m ago" />
        <AlertRow channel="slack" icon={MessageSquare} title="Strike-off warning" meta="Kennington Cabs · 1h ago" />
      </div>
    </div>
  );
}

function AlertRow({
  channel,
  icon: Icon,
  title,
  meta,
}: {
  channel: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  meta: string;
}) {
  return (
    <div className="px-4 py-2.5 grid grid-cols-[auto_1fr_auto] items-center gap-3">
      <div className="w-6 h-6 rounded-sm bg-navy-50 flex items-center justify-center">
        <Icon className="w-3 h-3 text-navy-700" />
      </div>
      <div className="min-w-0">
        <div className="text-[11px] font-medium text-navy-900 truncate">{title}</div>
        <div className="text-[10px] text-navy-500 truncate">{meta}</div>
      </div>
      <div className="flex items-center gap-1">
        <CheckCircle2 className="w-3 h-3 text-risk-low" />
        <span className="text-[9px] uppercase tracking-wider2 text-navy-500">{channel}</span>
      </div>
    </div>
  );
}

// ============================================================
// RISK HEATMAP — sectors × risk levels
// ============================================================
function RiskHeatmap() {
  // Find max across all cells for color scaling
  const allValues = Object.values(HEATMAP).flat();
  const maxVal = Math.max(...allValues);

  function cellStyle(val: number, levelIdx: number) {
    const ratio = val / maxVal;
    const baseColors = [
      // critical → high → medium → low (deep red to soft cream)
      'rgba(193, 60, 60, ', // critical
      'rgba(217, 119, 49, ', // high
      'rgba(214, 178, 92, ', // medium
      'rgba(91, 138, 99, ',  // low
    ];
    return {
      backgroundColor: `${baseColors[levelIdx]}${(0.15 + ratio * 0.7).toFixed(2)})`,
    };
  }

  return (
    <div className="bg-white border border-navy-200/50 rounded-sm p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-navy-500" />
          <span className="eyebrow">Risk distribution by sector</span>
        </div>
        <span className="text-[10px] text-navy-500">tracked count</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[11px] min-w-[480px]">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider2 text-navy-500">
              <th className="text-left font-medium py-1 pr-3" />
              {SECTORS.map((s) => (
                <th key={s} className="text-center font-medium py-1 px-1">{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LEVELS.map((level, levelIdx) => (
              <tr key={level}>
                <td className="py-1 pr-3 font-medium text-navy-700 text-[10px] uppercase tracking-wider2">
                  {level}
                </td>
                {SECTORS.map((sector) => {
                  const val = HEATMAP[sector][levelIdx];
                  return (
                    <td key={sector} className="p-0.5">
                      <div
                        className="h-7 rounded-sm flex items-center justify-center font-mono tabular-nums text-navy-900 text-[10px] transition-transform hover:scale-105 hover:shadow-sm cursor-default"
                        style={cellStyle(val, levelIdx)}
                      >
                        {val}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// KPI CARD
// ============================================================
function Kpi({
  label,
  value,
  delta,
  tone,
}: {
  label: string;
  value: string;
  delta?: string;
  tone: 'navy' | 'gold' | 'risk';
}) {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm p-3 lg:p-4 relative overflow-hidden lift">
      <div className="eyebrow text-[10px]">{label}</div>
      <div
        className={`display text-2xl lg:text-3xl tabular-nums mt-1 ${
          tone === 'gold' ? 'text-accent' :
          tone === 'risk' ? 'text-risk-critical' :
          'text-navy-900'
        }`}
      >
        {value}
      </div>
      {delta && <div className="text-[10px] text-navy-500 mt-1">{delta}</div>}
      <span className={`absolute right-0 top-0 h-full w-0.5 ${
        tone === 'gold' ? 'bg-accent' :
        tone === 'risk' ? 'bg-risk-critical' :
        'bg-navy-700'
      }`} />
    </div>
  );
}
