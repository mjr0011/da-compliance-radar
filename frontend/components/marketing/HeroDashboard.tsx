'use client';

/**
 * Hero dashboard mockup.
 *
 * Six widgets composed to look like a real product screenshot:
 *   1. Overdue Accounts (KPI + sparkline)
 *   2. AI Lead Score (radial gauge)
 *   3. Compliance Risk Meter (segmented bar with cursor)
 *   4. Upcoming Deadlines (list)
 *   5. Live UK Company Feed (animated stream)
 *   6. CRM Pipeline (mini kanban columns)
 *
 * All data is fictional but plausible — UK company numbers, London
 * postcodes, real SIC categories from the spec. The "live feed"
 * cycles entries to add motion without being distracting.
 */

import { useEffect, useState } from 'react';
import {
  TrendingUp,
  Activity,
  Calendar,
  Radio,
  Workflow,
  Brain,
  AlertTriangle,
} from 'lucide-react';

const FEED_ITEMS = [
  { id: 1, name: 'Thornbury Construction Ltd', meta: 'CRN 09182734 · SW9', tag: 'accounts overdue', tone: 'critical' },
  { id: 2, name: 'Camden Property Holdings', meta: 'CRN 11738490 · NW1', tag: 'confirmation due 5d', tone: 'high' },
  { id: 3, name: 'Pixel & Pine Studios', meta: 'CRN 13902187 · E2', tag: 'newly incorporated', tone: 'medium' },
  { id: 4, name: 'Mercer & Vale Consultants', meta: 'CRN 12384902 · EC2', tag: 'CIS scheme detected', tone: 'high' },
  { id: 5, name: 'Bow Lane Bakeries Ltd', meta: 'CRN 14029384 · E14', tag: 'dormant → active', tone: 'medium' },
  { id: 6, name: 'Highbury Care Group', meta: 'CRN 10398472 · N5', tag: 'officer churn', tone: 'high' },
];

const TONE_STYLES: Record<string, string> = {
  critical: 'bg-risk-critical/10 text-risk-critical border-risk-critical/30',
  high:     'bg-risk-high/10 text-risk-high border-risk-high/30',
  medium:   'bg-risk-medium/10 text-risk-medium border-risk-medium/30',
  low:      'bg-risk-low/10 text-risk-low border-risk-low/30',
};

export function HeroDashboard() {
  const [feedOffset, setFeedOffset] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setFeedOffset((o) => (o + 1) % FEED_ITEMS.length), 2800);
    return () => clearInterval(t);
  }, []);

  const visibleFeed = [
    FEED_ITEMS[feedOffset % FEED_ITEMS.length],
    FEED_ITEMS[(feedOffset + 1) % FEED_ITEMS.length],
    FEED_ITEMS[(feedOffset + 2) % FEED_ITEMS.length],
  ];

  return (
    <div className="relative max-w-md mx-auto lg:max-w-none">
      {/* Ambient halo */}
      <div className="absolute -inset-8 ambient-glow pointer-events-none" />

      <div className="relative grid grid-cols-2 gap-3 lg:gap-4 float-slow">
        {/* --- Card 1 — Overdue Accounts --- */}
        <Card>
          <CardHeader icon={AlertTriangle} eyebrow="Overdue accounts" trend="+12.4%" />
          <div className="display text-4xl text-navy-900 tabular-nums leading-none mt-2">1,847</div>
          <div className="text-[10px] text-navy-500 mt-1">across tracked UK Ltd companies</div>
          <Sparkline values={[12, 14, 13, 16, 17, 16, 19, 18, 21, 22, 24, 23]} />
        </Card>

        {/* --- Card 2 — AI Lead Score (radial gauge) --- */}
        <Card>
          <CardHeader icon={Brain} eyebrow="AI lead score" />
          <div className="flex items-center justify-between mt-1">
            <RadialGauge value={87} />
            <div className="text-right">
              <div className="display text-3xl tabular-nums text-accent leading-none">87</div>
              <div className="text-[10px] uppercase tracking-wider2 text-accent mt-1">very high</div>
              <div className="text-[10px] text-navy-500 mt-2">Thornbury Co.</div>
            </div>
          </div>
        </Card>

        {/* --- Card 3 — Compliance Risk Meter --- */}
        <Card className="col-span-2">
          <CardHeader icon={Activity} eyebrow="Compliance risk meter" />
          <RiskMeter level={72} />
          <div className="flex items-center justify-between mt-2 text-[10px] text-navy-500">
            <span>847 low</span>
            <span>523 medium</span>
            <span className="text-risk-high font-medium">312 high</span>
            <span className="text-risk-critical font-medium">147 critical</span>
          </div>
        </Card>

        {/* --- Card 4 — Upcoming Deadlines --- */}
        <Card>
          <CardHeader icon={Calendar} eyebrow="Upcoming deadlines" />
          <div className="space-y-2 mt-2">
            <DeadlineRow name="Cobble Yard Studios" days={3} kind="confirmation" />
            <DeadlineRow name="Penny Lane Retail" days={7} kind="accounts" />
            <DeadlineRow name="Quill & Ink Ltd" days={11} kind="accounts" />
          </div>
        </Card>

        {/* --- Card 5 — CRM Pipeline --- */}
        <Card>
          <CardHeader icon={Workflow} eyebrow="CRM pipeline" />
          <div className="grid grid-cols-4 gap-1 mt-2">
            <PipelineCol label="New" count={24} color="bg-navy-300" />
            <PipelineCol label="Qual" count={18} color="bg-navy-500" />
            <PipelineCol label="Contact" count={11} color="bg-navy-700" />
            <PipelineCol label="Won" count={6} color="bg-accent" />
          </div>
          <div className="text-[10px] text-navy-500 mt-2">£94k pipeline value · 7-day</div>
        </Card>

        {/* --- Card 6 — Live UK Company Feed --- */}
        <Card className="col-span-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Radio className="w-3 h-3 text-accent" />
              <span className="eyebrow">Live UK company feed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
              <span className="text-[10px] uppercase tracking-wider2 text-accent">live</span>
            </div>
          </div>
          <div className="space-y-1.5">
            {visibleFeed.map((item, i) => (
              <div
                key={`${item.id}-${feedOffset}-${i}`}
                className="slide-in-right grid grid-cols-[1fr_auto] gap-3 items-center"
              >
                <div className="min-w-0">
                  <div className="text-[12px] font-medium text-navy-900 truncate">{item.name}</div>
                  <div className="font-mono text-[10px] text-navy-500 truncate">{item.meta}</div>
                </div>
                <span className={`pill border ${TONE_STYLES[item.tone]} whitespace-nowrap text-[10px] ${item.tone === 'critical' ? 'glow-pulse' : ''}`}>
                  {item.tag}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// --- Building blocks ---

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`relative bg-white border border-navy-200/50 rounded-sm shadow-card p-4 ${className}`}
    >
      {children}
    </div>
  );
}

function CardHeader({
  icon: Icon,
  eyebrow,
  trend,
}: {
  icon: React.ComponentType<{ className?: string }>;
  eyebrow: string;
  trend?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3 text-navy-500" />
        <span className="eyebrow">{eyebrow}</span>
      </div>
      {trend && (
        <span className="flex items-center gap-1 text-[10px] text-accent font-medium">
          <TrendingUp className="w-2.5 h-2.5" />
          {trend}
        </span>
      )}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  // viewBox is 100x30, so map y into 4..26 range for breathing room
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 26 - ((v - min) / range) * 22;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="w-full h-7 mt-2">
      <polyline
        fill="none"
        stroke="#c89b3c"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

function RadialGauge({ value }: { value: number }) {
  const r = 22;
  const c = 2 * Math.PI * r;
  const dash = (value / 100) * c;
  return (
    <svg viewBox="0 0 56 56" className="w-14 h-14">
      <circle cx="28" cy="28" r={r} fill="none" stroke="#e8e1ce" strokeWidth="4" />
      <circle
        cx="28"
        cy="28"
        r={r}
        fill="none"
        stroke="#c89b3c"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c}`}
        transform="rotate(-90 28 28)"
      />
    </svg>
  );
}

function RiskMeter({ level }: { level: number }) {
  // Segmented bar: 4 segments (low/med/high/critical) with a needle marker
  return (
    <div className="mt-2 relative">
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        <div className="flex-1 bg-risk-low/60" />
        <div className="flex-1 bg-risk-medium/60" />
        <div className="flex-1 bg-risk-high/70" />
        <div className="flex-1 bg-risk-critical/70" />
      </div>
      <div
        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
        style={{ left: `${level}%` }}
      >
        <div className="w-2.5 h-2.5 rounded-full bg-navy-900 ring-2 ring-cream-50" />
      </div>
    </div>
  );
}

function DeadlineRow({
  name,
  days,
  kind,
}: {
  name: string;
  days: number;
  kind: 'accounts' | 'confirmation';
}) {
  const urgent = days <= 5;
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="min-w-0">
        <div className="text-[11px] font-medium text-navy-900 truncate">{name}</div>
        <div className="text-[9px] uppercase tracking-wider2 text-navy-500">{kind}</div>
      </div>
      <div className={`text-[11px] tabular-nums font-medium ${urgent ? 'text-risk-critical' : 'text-navy-700'}`}>
        {days}d
      </div>
    </div>
  );
}

function PipelineCol({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center">
      <div className={`w-full h-8 ${color} rounded-sm flex items-center justify-center text-[10px] font-medium text-cream-50 tabular-nums`}>
        {count}
      </div>
      <div className="text-[9px] uppercase tracking-wider2 text-navy-500 mt-1">{label}</div>
    </div>
  );
}
