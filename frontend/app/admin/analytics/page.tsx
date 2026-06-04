'use client';

/**
 * Admin analytics dashboard.
 *
 * Visualises the aggregated stats from /api/admin/analytics:
 *   - Lead funnel (by status)
 *   - Lead urgency mix
 *   - Alert delivery health by channel
 *   - Risk distribution
 *   - Top audit events in last 30 days
 *   - Total pipeline value (active statuses)
 *
 * All charts are custom SVG/divs — no Recharts dependency. Keeps the
 * bundle lean and the visual language consistent with the rest of the
 * editorial design.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import {
  StatCard,
  StatCardSkeleton,
  Empty,
  ErrorState,
} from '@/components/ui';
import { formatGBP } from '@/lib/format';
import {
  TrendingUp,
  Sparkles,
  BellRing,
  ScrollText,
  ShieldAlert,
  BarChart3,
} from 'lucide-react';
import { clsx } from 'clsx';

// ============================================================
// STATIC METADATA
// ============================================================

const STATUS_ORDER = ['new', 'qualified', 'contacted', 'in_progress', 'won', 'lost', 'rejected'] as const;
const URGENCY_ORDER = ['urgent', 'high', 'medium', 'low'] as const;
const RISK_ORDER = ['critical', 'high', 'medium', 'low'] as const;

const STATUS_COLORS: Record<string, string> = {
  new:          'bg-navy-300',
  qualified:    'bg-navy-500',
  contacted:    'bg-navy-700',
  in_progress:  'bg-accent',
  won:          'bg-risk-low',
  lost:         'bg-navy-200',
  rejected:     'bg-risk-critical/40',
};

const URGENCY_COLORS: Record<string, string> = {
  urgent: 'bg-risk-critical',
  high:   'bg-risk-high',
  medium: 'bg-risk-medium',
  low:    'bg-risk-low',
};

const RISK_COLORS: Record<string, string> = {
  critical: 'bg-risk-critical',
  high:     'bg-risk-high',
  medium:   'bg-risk-medium',
  low:      'bg-risk-low',
};

const CHANNEL_LABELS: Record<string, string> = {
  slack:    'Slack',
  email:    'Email',
  telegram: 'Telegram',
};

// ============================================================
// PAGE
// ============================================================
export default function AnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics'],
    queryFn: api.analytics,
    refetchInterval: 60_000,
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title="Platform analytics"
        description="Operational metrics across leads, alerts, compliance risk, and audit activity. Refreshes every 60 seconds."
        actions={
          <div className="flex items-center gap-2 text-xs text-navy-500">
            <BarChart3 className="w-3.5 h-3.5 text-accent" />
            30-day rolling
          </div>
        }
      />

      <div className="px-6 lg:px-10 py-8 space-y-10">
        {error && (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        )}

        {/* Top-line stats */}
        <section>
          <h2 className="eyebrow mb-4">Headlines</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 fade-up-stagger">
            {isLoading || !data ? (
              <>
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
              </>
            ) : (
              <>
                <StatCard
                  label="Pipeline value"
                  value={formatGBP(data.pipeline_value_gbp)}
                  accent="gold"
                  delta="Active statuses"
                />
                <StatCard
                  label="Total leads"
                  value={Object.values(data.leads_by_status)
                    .reduce((a, b) => a + b, 0)
                    .toLocaleString('en-GB')}
                />
                <StatCard
                  label="Total alerts dispatched"
                  value={Object.values(data.alerts_by_channel)
                    .flatMap((c) => Object.values(c))
                    .reduce((a, b) => a + b, 0)
                    .toLocaleString('en-GB')}
                />
                <StatCard
                  label="High-risk companies"
                  value={(
                    (data.risk_distribution.critical || 0) + (data.risk_distribution.high || 0)
                  ).toLocaleString('en-GB')}
                  accent="risk"
                />
              </>
            )}
          </div>
        </section>

        {/* Funnel + urgency */}
        <section className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="eyebrow">Lead funnel</h2>
              <span className="flex items-center gap-1.5 text-xs text-navy-500">
                <Sparkles className="w-3.5 h-3.5 text-accent" />
                by status
              </span>
            </div>
            {isLoading || !data ? (
              <FunnelSkeleton />
            ) : (
              <FunnelChart data={data.leads_by_status} />
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="eyebrow">Urgency mix</h2>
              <span className="flex items-center gap-1.5 text-xs text-navy-500">
                <TrendingUp className="w-3.5 h-3.5 text-accent" />
                by urgency
              </span>
            </div>
            {isLoading || !data ? (
              <RingSkeleton />
            ) : (
              <DonutChart
                data={data.leads_by_urgency}
                order={URGENCY_ORDER}
                colors={URGENCY_COLORS}
              />
            )}
          </div>
        </section>

        {/* Alert delivery health */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="eyebrow">Alert delivery health</h2>
            <span className="flex items-center gap-1.5 text-xs text-navy-500">
              <BellRing className="w-3.5 h-3.5 text-accent" />
              sent · failed · pending
            </span>
          </div>
          {isLoading || !data ? (
            <ChannelSkeleton />
          ) : Object.keys(data.alerts_by_channel).length === 0 ? (
            <Empty
              icon={BellRing}
              title="No alerts yet"
              description="Once leads start triggering alerts, deliverability stats will populate here."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(data.alerts_by_channel).map(([channel, breakdown]) => (
                <ChannelCard key={channel} channel={channel} breakdown={breakdown} />
              ))}
            </div>
          )}
        </section>

        {/* Risk distribution + audit events */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="eyebrow">Compliance risk distribution</h2>
              <span className="flex items-center gap-1.5 text-xs text-navy-500">
                <ShieldAlert className="w-3.5 h-3.5 text-risk-high" />
                companies tracked
              </span>
            </div>
            {isLoading || !data ? (
              <BarsSkeleton />
            ) : (
              <RiskBars data={data.risk_distribution} />
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="eyebrow">Top audit events</h2>
              <span className="flex items-center gap-1.5 text-xs text-navy-500">
                <ScrollText className="w-3.5 h-3.5 text-accent" />
                last 30 days
              </span>
            </div>
            {isLoading || !data ? (
              <BarsSkeleton />
            ) : data.audit_events_30d.length === 0 ? (
              <Empty
                icon={ScrollText}
                title="No audit events yet"
                description="Audit events are recorded on login, status change, and admin action."
              />
            ) : (
              <AuditEventsList events={data.audit_events_30d} />
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

// ============================================================
// FUNNEL CHART — horizontal stacked bars per status
// ============================================================
function FunnelChart({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (total === 0) {
    return (
      <Empty
        icon={Sparkles}
        title="No leads yet"
        description="Once the scoring engine promotes companies above 40 points, they'll appear in this funnel."
      />
    );
  }

  return (
    <div className="card p-5 space-y-3">
      {STATUS_ORDER.map((status) => {
        const count = data[status] || 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div key={status}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-navy-700 capitalize">{status.replace('_', ' ')}</span>
              <span className="font-mono tabular-nums text-navy-900">
                {count.toLocaleString('en-GB')}
                <span className="text-navy-400 ml-2">{pct.toFixed(1)}%</span>
              </span>
            </div>
            <div className="h-2 bg-navy-100 rounded-full overflow-hidden">
              <div
                className={clsx('h-full grow-up rounded-full', STATUS_COLORS[status])}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// DONUT CHART — for urgency mix
// ============================================================
function DonutChart<T extends string>({
  data,
  order,
  colors,
}: {
  data: Record<string, number>;
  order: readonly T[];
  colors: Record<string, string>;
}) {
  const total = order.reduce((sum, k) => sum + (data[k] || 0), 0);
  if (total === 0) {
    return (
      <Empty
        icon={TrendingUp}
        title="Nothing to display"
        description="No data in this segment yet."
      />
    );
  }

  // Build cumulative percentages and pick a stroke-dasharray per segment
  const R = 36;
  const C = 2 * Math.PI * R;
  let cumulative = 0;

  // Map color class → actual CSS color so SVG stroke can render directly.
  // (We can't put a Tailwind class on an SVG <circle> stroke.)
  const RAW_COLORS: Record<string, string> = {
    'bg-risk-critical': '#c13c3c',
    'bg-risk-high':     '#d97731',
    'bg-risk-medium':   '#d6b25c',
    'bg-risk-low':      '#5b8a63',
    'bg-navy-700':      '#2a3e6e',
    'bg-navy-500':      '#4a5b85',
    'bg-navy-300':      '#7c89ac',
    'bg-navy-200':      '#a5afcb',
    'bg-accent':        '#c89b3c',
  };

  return (
    <div className="card p-5 flex items-center gap-5">
      <svg viewBox="0 0 100 100" className="w-32 h-32 flex-shrink-0 -rotate-90">
        <circle cx="50" cy="50" r={R} fill="none" stroke="#e8e1ce" strokeWidth="14" />
        {order.map((key) => {
          const value = data[key] || 0;
          const pct = value / total;
          if (pct === 0) return null;
          const dash = pct * C;
          const offset = -cumulative * C;
          const colorClass = colors[key] || 'bg-navy-500';
          const stroke = RAW_COLORS[colorClass] || '#4a5b85';
          cumulative += pct;
          return (
            <circle
              key={key}
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke={stroke}
              strokeWidth="14"
              strokeDasharray={`${dash} ${C - dash}`}
              strokeDashoffset={offset}
            />
          );
        })}
      </svg>

      <div className="space-y-2 flex-1 text-xs">
        {order.map((key) => {
          const value = data[key] || 0;
          const pct = total > 0 ? (value / total) * 100 : 0;
          return (
            <div key={key} className="flex items-center gap-2">
              <span className={clsx('w-2 h-2 rounded-full shrink-0', colors[key])} />
              <span className="capitalize text-navy-700">{key}</span>
              <span className="ml-auto font-mono tabular-nums text-navy-900">
                {value.toLocaleString('en-GB')}
              </span>
              <span className="font-mono tabular-nums text-navy-400 w-10 text-right">
                {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================
// CHANNEL CARD — Slack/Email/Telegram delivery
// ============================================================
function ChannelCard({
  channel,
  breakdown,
}: {
  channel: string;
  breakdown: Record<string, number>;
}) {
  const sent = breakdown.sent || 0;
  const failed = breakdown.failed || 0;
  const pending = breakdown.pending || 0;
  const total = sent + failed + pending;
  const rate = total > 0 ? (sent / total) * 100 : 0;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="eyebrow">{CHANNEL_LABELS[channel] || channel}</span>
        <span
          className={clsx(
            'pill border text-[10px]',
            rate >= 95 && 'bg-risk-low/10 text-risk-low border-risk-low/30',
            rate >= 80 && rate < 95 && 'bg-risk-medium/10 text-risk-medium border-risk-medium/30',
            rate < 80 && 'bg-risk-critical/10 text-risk-critical border-risk-critical/30',
          )}
        >
          {rate.toFixed(1)}% delivered
        </span>
      </div>

      <div className="display text-3xl text-navy-900 tabular-nums">
        {total.toLocaleString('en-GB')}
      </div>
      <div className="text-[10px] text-navy-500 mb-4">total alerts</div>

      <div className="flex h-1.5 rounded-full overflow-hidden bg-navy-100 mb-3">
        {sent > 0 && (
          <div className="bg-risk-low grow-up" style={{ width: `${(sent / total) * 100}%` }} />
        )}
        {failed > 0 && (
          <div className="bg-risk-critical grow-up" style={{ width: `${(failed / total) * 100}%` }} />
        )}
        {pending > 0 && (
          <div className="bg-navy-300 grow-up" style={{ width: `${(pending / total) * 100}%` }} />
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-navy-500 text-[10px]">Sent</div>
          <div className="font-mono tabular-nums text-risk-low">{sent.toLocaleString('en-GB')}</div>
        </div>
        <div>
          <div className="text-navy-500 text-[10px]">Failed</div>
          <div className="font-mono tabular-nums text-risk-critical">
            {failed.toLocaleString('en-GB')}
          </div>
        </div>
        <div>
          <div className="text-navy-500 text-[10px]">Pending</div>
          <div className="font-mono tabular-nums text-navy-700">{pending.toLocaleString('en-GB')}</div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// RISK BARS
// ============================================================
function RiskBars({ data }: { data: Record<string, number> }) {
  const max = Math.max(...RISK_ORDER.map((k) => data[k] || 0), 1);
  return (
    <div className="card p-5 space-y-3">
      {RISK_ORDER.map((level) => {
        const count = data[level] || 0;
        const pct = (count / max) * 100;
        return (
          <div key={level}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="capitalize text-navy-700">{level}</span>
              <span className="font-mono tabular-nums text-navy-900">
                {count.toLocaleString('en-GB')}
              </span>
            </div>
            <div className="h-2 bg-navy-100 rounded-full overflow-hidden">
              <div
                className={clsx('h-full grow-up rounded-full', RISK_COLORS[level])}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// AUDIT EVENTS LIST
// ============================================================
function AuditEventsList({
  events,
}: {
  events: { event_type: string; count: number }[];
}) {
  const max = Math.max(...events.map((e) => e.count), 1);
  return (
    <div className="card divide-y divide-navy-200/40">
      {events.map((e) => {
        const pct = (e.count / max) * 100;
        return (
          <div key={e.event_type} className="px-4 py-2.5 grid grid-cols-[1fr_auto] items-center gap-3">
            <div className="min-w-0">
              <div className="font-mono text-[10px] text-navy-700 truncate">{e.event_type}</div>
              <div className="h-1 bg-navy-100 rounded-full overflow-hidden mt-1.5">
                <div className="h-full bg-navy-500 grow-up rounded-full" style={{ width: `${pct}%` }} />
              </div>
            </div>
            <div className="font-mono tabular-nums text-xs text-navy-900 w-12 text-right">
              {e.count.toLocaleString('en-GB')}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// SKELETONS
// ============================================================
function FunnelSkeleton() {
  return (
    <div className="card p-5 space-y-3">
      {[1, 2, 3, 4, 5, 6, 7].map((i) => (
        <div key={i}>
          <div className="flex items-center justify-between mb-1">
            <div className="skeleton h-3 w-20" />
            <div className="skeleton h-3 w-12" />
          </div>
          <div className="skeleton h-2 w-full rounded-full" />
        </div>
      ))}
    </div>
  );
}

function RingSkeleton() {
  return (
    <div className="card p-5 flex items-center gap-5">
      <div className="skeleton w-32 h-32 rounded-full shrink-0" />
      <div className="space-y-2 flex-1">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton h-4 w-full" />
        ))}
      </div>
    </div>
  );
}

function ChannelSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="card p-5">
          <div className="skeleton h-3 w-20 mb-3" />
          <div className="skeleton h-9 w-24 mb-2" />
          <div className="skeleton h-1.5 w-full rounded-full mb-3" />
          <div className="grid grid-cols-3 gap-2">
            <div className="skeleton h-8" />
            <div className="skeleton h-8" />
            <div className="skeleton h-8" />
          </div>
        </div>
      ))}
    </div>
  );
}

function BarsSkeleton() {
  return (
    <div className="card p-5 space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i}>
          <div className="flex items-center justify-between mb-1">
            <div className="skeleton h-3 w-20" />
            <div className="skeleton h-3 w-10" />
          </div>
          <div className="skeleton h-2 w-full rounded-full" />
        </div>
      ))}
    </div>
  );
}
