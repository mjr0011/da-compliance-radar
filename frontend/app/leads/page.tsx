'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Lead } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import {
  UrgencyPill,
  ScoreBar,
  CardSkeleton,
  Empty,
  ErrorState,
} from '@/components/ui';
import { formatGBP, formatRelative } from '@/lib/format';
import { Bell, Cloud, Sparkles } from 'lucide-react';

const STATUSES = ['new', 'qualified', 'contacted', 'in_progress', 'won', 'lost', 'rejected'];
const URGENCIES = ['urgent', 'high', 'medium', 'low'];

export default function LeadsPage() {
  const [status, setStatus] = useState('');
  const [urgency, setUrgency] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 25;

  const qc = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['leads', { status, urgency, minScore, page }],
    queryFn: () =>
      api.listLeads({
        status: status || undefined,
        urgency: urgency || undefined,
        min_score: minScore || undefined,
        limit,
        offset: page * limit,
      }),
    placeholderData: (p) => p,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.updateLead(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  });

  const alertMutation = useMutation({
    mutationFn: (id: number) => api.fireLeadAlert(id),
  });

  const crmMutation = useMutation({
    mutationFn: (id: number) => api.syncLeadCrm(id),
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Opportunities"
        title="Leads"
        description="AI-classified accountancy opportunities. Update status, push to CRM or re-fire the alert."
      />

      <div className="px-6 lg:px-10 py-8 space-y-6">
        <div className="card p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-[200px_200px_140px_1fr] gap-3 items-end">
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Status
            </label>
            <select
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(0); }}
              className="input"
            >
              <option value="">All statuses</option>
              {STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Urgency
            </label>
            <select
              value={urgency}
              onChange={(e) => { setUrgency(e.target.value); setPage(0); }}
              className="input"
            >
              <option value="">All</option>
              {URGENCIES.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Min score
            </label>
            <input
              type="number" min={0} max={100}
              value={minScore || ''}
              onChange={(e) => { setMinScore(Number(e.target.value) || 0); setPage(0); }}
              className="input tabular-nums"
              placeholder="0"
            />
          </div>
          <div className="text-xs text-navy-500 tabular-nums lg:text-right col-span-2 md:col-span-1">
            {data ? `${data.total.toLocaleString('en-GB')} leads` : '—'}
          </div>
        </div>

        {error ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : isLoading && !data ? (
          <CardSkeleton count={4} />
        ) : !data || data.items.length === 0 ? (
          <Empty
            icon={Sparkles}
            title="No leads yet"
            description="Once the scoring engine promotes companies above 40 points, they'll appear here."
          />
        ) : (
          <>
            <div className="space-y-3 fade-up">
              {data.items.map((lead) => (
                <LeadCard
                  key={lead.id}
                  lead={lead}
                  onStatusChange={(status) => updateMutation.mutate({ id: lead.id, status })}
                  onFireAlert={() => alertMutation.mutate(lead.id)}
                  onPushCrm={() => crmMutation.mutate(lead.id)}
                />
              ))}
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

function LeadCard({
  lead,
  onStatusChange,
  onFireAlert,
  onPushCrm,
}: {
  lead: Lead;
  onStatusChange: (status: string) => void;
  onFireAlert: () => void;
  onPushCrm: () => void;
}) {
  return (
    <div className="card p-5 hover:border-navy-300/60 transition-colors">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <UrgencyPill urgency={lead.urgency} />
            {lead.ai_category && (
              <span className="text-[11px] uppercase tracking-wider2 text-accent">
                {lead.ai_category}
              </span>
            )}
            <span className="text-[11px] text-navy-400">
              · {formatRelative(lead.created_at)}
            </span>
          </div>
          <div className="display text-xl text-navy-900">
            {lead.company?.company_name || `Company #${lead.company_id}`}
          </div>
          {lead.company && (
            <div className="font-mono text-[11px] text-navy-500 mt-1">
              {lead.company.company_number}
              {lead.company.locality && <> · {lead.company.locality}</>}
              {lead.company.sic_description && <> · {lead.company.sic_description}</>}
            </div>
          )}
          {lead.summary && (
            <p className="mt-3 text-sm text-navy-700 leading-relaxed max-w-2xl">
              {lead.summary}
            </p>
          )}
        </div>

        <div className="flex flex-col items-start lg:items-end gap-3 min-w-[200px]">
          <div className="lg:text-right">
            <div className="eyebrow mb-1">Estimated value</div>
            <div className="display text-2xl text-accent">
              {formatGBP(lead.estimated_value_gbp)}
              <span className="text-xs font-sans text-navy-500">/yr</span>
            </div>
          </div>
          <ScoreBar score={lead.lead_score} label="lead score" />
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 mt-4 border-t border-navy-200/60 flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={lead.status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="text-xs bg-white border border-navy-200 rounded-sm px-2 py-1 capitalize"
          >
            {['new', 'qualified', 'contacted', 'in_progress', 'won', 'lost', 'rejected'].map((s) => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
          {lead.crm_provider && (
            <span className="text-[11px] text-navy-500">
              Synced to {lead.crm_provider}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={onFireAlert} className="btn-ghost text-xs">
            <Bell className="w-3.5 h-3.5" />
            Re-fire alert
          </button>
          <button onClick={onPushCrm} className="btn-ghost text-xs">
            <Cloud className="w-3.5 h-3.5" />
            Push to CRM
          </button>
        </div>
      </div>
    </div>
  );
}
