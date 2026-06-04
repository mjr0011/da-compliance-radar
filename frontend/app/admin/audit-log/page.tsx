'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import { Empty, ErrorState, TableSkeleton } from '@/components/ui';
import { formatRelative } from '@/lib/format';
import { ScrollText, Search, Shield } from 'lucide-react';
import { clsx } from 'clsx';

const EVENT_GROUPS: Record<string, string> = {
  'auth.login.success': 'bg-risk-low/10 text-risk-low',
  'auth.login.failed': 'bg-risk-high/10 text-risk-high',
  'auth.login.locked': 'bg-risk-critical/10 text-risk-critical',
  'auth.logout': 'bg-navy-100 text-navy-700',
  'auth.token.refresh': 'bg-navy-100 text-navy-700',
  'auth.token.refresh.failed': 'bg-risk-high/10 text-risk-high',
  'user.created': 'bg-accent/15 text-accent',
  'suppression.added': 'bg-accent/15 text-accent',
  'suppression.removed': 'bg-navy-100 text-navy-700',
};

export default function AuditLogPage() {
  const [eventType, setEventType] = useState('');
  const [page, setPage] = useState(0);
  const limit = 50;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-log', { eventType, page }],
    queryFn: () => api.listAuditLog({
      event_type: eventType || undefined,
      limit,
      offset: page * limit,
    }),
    placeholderData: (p) => p,
    refetchInterval: 30_000,
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title="Audit log"
        description="Append-only record of every security-relevant event. Used for compliance reporting and incident review."
        actions={
          <div className="flex items-center gap-2 text-xs text-navy-500">
            <Shield className="w-3.5 h-3.5 text-accent" />
            Read-only · GDPR audit trail
          </div>
        }
      />

      <div className="px-6 lg:px-10 py-8 space-y-6">
        <div className="card p-4 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[240px]">
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Event type
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-navy-400" />
              <input
                value={eventType}
                onChange={(e) => { setEventType(e.target.value); setPage(0); }}
                placeholder="e.g. auth.login.failed"
                className="input pl-8"
              />
            </div>
          </div>
          <div className="text-xs text-navy-500 tabular-nums">
            {data ? `${data.total.toLocaleString('en-GB')} events` : '—'}
          </div>
        </div>

        {error ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : isLoading && !data ? (
          <TableSkeleton rows={10} cols={5} />
        ) : !data || data.items.length === 0 ? (
          <Empty
            icon={ScrollText}
            title="No audit events match"
            description="Adjust the filter or wait for activity. Every login, logout, token refresh and admin action is recorded here."
          />
        ) : (
          <>
            <div className="card overflow-hidden fade-up">
              <table className="w-full text-sm">
                <thead className="bg-navy-50 border-b border-navy-200/60">
                  <tr className="text-[11px] uppercase tracking-wider2 text-navy-500">
                    <th className="text-left font-medium px-5 py-3">Event</th>
                    <th className="text-left font-medium px-5 py-3">Actor</th>
                    <th className="text-left font-medium px-5 py-3">Target</th>
                    <th className="text-left font-medium px-5 py-3">IP / agent</th>
                    <th className="text-right font-medium px-5 py-3">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-200/40">
                  {data.items.map((entry) => (
                    <tr key={entry.id} className="hover:bg-cream-50/40 transition-colors">
                      <td className="px-5 py-3">
                        <span
                          className={clsx(
                            'pill font-mono text-[10px]',
                            EVENT_GROUPS[entry.event_type] || 'bg-navy-100 text-navy-700',
                          )}
                        >
                          {entry.event_type}
                        </span>
                        {entry.detail && Object.keys(entry.detail).length > 0 && (
                          <div className="font-mono text-[10px] text-navy-500 mt-1 truncate max-w-xs">
                            {JSON.stringify(entry.detail)}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3 text-xs">
                        <div className="font-medium text-navy-900">
                          {entry.actor_email || <span className="text-navy-400">—</span>}
                        </div>
                        {entry.actor_id && (
                          <div className="text-navy-500 font-mono text-[10px]">
                            #{entry.actor_id}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3 text-xs">
                        {entry.target_type ? (
                          <span className="text-navy-700">
                            {entry.target_type}
                            {entry.target_id && (
                              <span className="font-mono text-navy-500"> #{entry.target_id}</span>
                            )}
                          </span>
                        ) : (
                          <span className="text-navy-400">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-xs">
                        <div className="font-mono text-navy-700">
                          {entry.actor_ip || '—'}
                        </div>
                        {entry.actor_user_agent && (
                          <div className="text-navy-500 truncate max-w-[180px]" title={entry.actor_user_agent}>
                            {entry.actor_user_agent}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3 text-xs text-right text-navy-500 whitespace-nowrap">
                        {formatRelative(entry.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between text-sm pt-2 flex-wrap gap-3">
              <div className="text-navy-500">
                Showing {data.offset + 1}–{Math.min(data.offset + data.items.length, data.total)}
                {' '}of {data.total.toLocaleString('en-GB')}
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="btn-ghost disabled:opacity-30"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >← Prev</button>
                <button
                  className="btn-ghost disabled:opacity-30"
                  disabled={data.offset + data.items.length >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >Next →</button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
