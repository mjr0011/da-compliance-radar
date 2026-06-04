'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import {
  StatCard,
  StatCardSkeleton,
  Empty,
  ErrorState,
} from '@/components/ui';
import { AlertTriangle, TrendingUp, Radar } from 'lucide-react';

export default function DashboardPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
    refetchInterval: 60_000,
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Overview"
        title="Compliance & lead intelligence"
        description="Live signals from Companies House, intent monitoring, and the AI classifier. Refreshes every 60 seconds."
      />

      <div className="px-6 lg:px-10 py-8 space-y-10">
        {error && (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        )}

        {/* At a glance */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="eyebrow">At a glance</h2>
          </div>
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
                  label="Companies tracked"
                  value={data.stats.total_companies_tracked.toLocaleString('en-GB')}
                />
                <StatCard
                  label="High-value leads"
                  value={data.stats.high_value_leads.toLocaleString('en-GB')}
                  accent="gold"
                  delta="Score ≥ 70"
                />
                <StatCard
                  label="New leads (7d)"
                  value={data.stats.new_leads_7d.toLocaleString('en-GB')}
                />
                <StatCard
                  label="Alerts sent (24h)"
                  value={data.stats.alerts_sent_24h.toLocaleString('en-GB')}
                />
              </>
            )}
          </div>
        </section>

        {/* Compliance risk */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="eyebrow">Compliance risk</h2>
            <div className="flex items-center gap-2 text-xs text-navy-500">
              <AlertTriangle className="w-3.5 h-3.5 text-risk-high" />
              Companies House signals
            </div>
          </div>
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
                  label="Overdue accounts"
                  value={data.stats.overdue_accounts_count.toLocaleString('en-GB')}
                  accent="risk"
                />
                <StatCard
                  label="Overdue confirmation"
                  value={data.stats.overdue_confirmation_count.toLocaleString('en-GB')}
                  accent="risk"
                />
                <StatCard
                  label="Strike-off warnings"
                  value={data.stats.strike_off_warnings.toLocaleString('en-GB')}
                  accent="risk"
                />
                <StatCard
                  label="High-risk companies"
                  value={data.stats.high_risk_companies.toLocaleString('en-GB')}
                />
              </>
            )}
          </div>
        </section>

        {/* Top sectors */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="eyebrow">Top sectors</h2>
            <div className="flex items-center gap-2 text-xs text-navy-500">
              <TrendingUp className="w-3.5 h-3.5 text-accent" />
              Ranked by tracked count
            </div>
          </div>
          {isLoading || !data ? (
            <div className="card divide-y divide-navy-200/60">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-6 px-5 py-3.5">
                  <div className="skeleton h-4 w-3/5" />
                  <div className="skeleton h-3 w-20" />
                  <div className="skeleton h-3 w-12" />
                </div>
              ))}
            </div>
          ) : data.top_sectors.length === 0 ? (
            <Empty
              icon={Radar}
              title="No sector data yet"
              description="Once the worker has fetched companies from Companies House, this breakdown will populate."
            />
          ) : (
            <div className="card divide-y divide-navy-200/60 fade-up">
              {data.top_sectors.map((s) => (
                <div
                  key={s.sic_description}
                  className="grid grid-cols-[1fr_auto_auto] items-center gap-6 px-5 py-3"
                >
                  <div className="text-sm font-medium text-navy-900">
                    {s.sic_description}
                  </div>
                  <div className="text-xs text-navy-500 tabular-nums">
                    {s.count.toLocaleString('en-GB')} tracked
                  </div>
                  <div className="font-mono text-xs tabular-nums text-navy-700">
                    avg {s.avg_lead_score}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
