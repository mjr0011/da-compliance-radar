'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import { Empty, ErrorState } from '@/components/ui';
import { formatRelative } from '@/lib/format';
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  MessageSquare,
  Send,
  Mail,
  BellRing,
} from 'lucide-react';
import { clsx } from 'clsx';

const CHANNEL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  telegram: Send,
  email: Mail,
};

export default function AlertsPage() {
  const [channel, setChannel] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['alerts', { channel, statusFilter }],
    queryFn: () => api.listAlerts({
      channel: channel || undefined,
      status: statusFilter || undefined,
    }),
    refetchInterval: 30_000,
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Activity"
        title="Alert history"
        description="Every alert the platform has dispatched, across all configured channels. Refreshes every 30 seconds."
      />

      <div className="px-6 lg:px-10 py-8 space-y-6">
        <div className="card p-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Channel
            </label>
            <select value={channel} onChange={(e) => setChannel(e.target.value)} className="input min-w-[160px]">
              <option value="">All channels</option>
              <option value="slack">Slack</option>
              <option value="telegram">Telegram</option>
              <option value="email">Email</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Status
            </label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input min-w-[160px]">
              <option value="">All statuses</option>
              <option value="sent">Sent</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="text-xs text-navy-500 ml-auto">
            {data ? `${data.length.toLocaleString('en-GB')} entries` : '—'}
          </div>
        </div>

        {error ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : isLoading && !data ? (
          <div className="card divide-y divide-navy-200/40">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="grid grid-cols-[auto_auto_1fr_auto] gap-4 items-center px-5 py-3">
                <div className="skeleton w-9 h-9 rounded-sm" />
                <div className="skeleton h-3 w-16" />
                <div className="space-y-1.5">
                  <div className="skeleton h-3.5 w-1/3" />
                </div>
                <div className="skeleton h-3 w-20" />
              </div>
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <Empty
            icon={BellRing}
            title="No alerts yet"
            description="Once a high-value lead is created, the alert dispatcher will fan it out to every configured channel."
          />
        ) : (
          <div className="card divide-y divide-navy-200/40 fade-up">
            {data.map((a) => {
              const Icon = CHANNEL_ICONS[a.alert_channel] || MessageSquare;
              const status = a.sent_status;
              return (
                <div key={a.id} className="grid grid-cols-[auto_auto_1fr_auto] gap-4 items-center px-5 py-3 hover:bg-cream-50/40 transition-colors">
                  <div
                    className={clsx(
                      'w-9 h-9 rounded-sm flex items-center justify-center',
                      status === 'sent' && 'bg-risk-low/10 text-risk-low',
                      status === 'failed' && 'bg-risk-critical/10 text-risk-critical',
                      status === 'pending' && 'bg-navy-100 text-navy-500',
                    )}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="text-xs uppercase tracking-wider2 text-navy-500 w-20">
                    {a.alert_channel}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-navy-900 capitalize">
                      {a.alert_type.replace(/_/g, ' ')}
                    </div>
                    {a.error_message && (
                      <div className="text-[11px] text-risk-critical mt-0.5 truncate">
                        {a.error_message}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-navy-500 whitespace-nowrap">
                    {status === 'sent' && <CheckCircle2 className="w-3.5 h-3.5 text-risk-low" />}
                    {status === 'failed' && <AlertCircle className="w-3.5 h-3.5 text-risk-critical" />}
                    {status === 'pending' && <Clock className="w-3.5 h-3.5" />}
                    {formatRelative(a.sent_at || a.created_at)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
