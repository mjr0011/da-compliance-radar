'use client';

import { clsx } from 'clsx';
import { riskColor, urgencyColor } from '@/lib/format';
import { Inbox, AlertCircle, RefreshCw } from 'lucide-react';

export function StatCard({
  label,
  value,
  delta,
  accent,
}: {
  label: string;
  value: string | number;
  delta?: string;
  accent?: 'navy' | 'gold' | 'risk';
}) {
  return (
    <div className="card p-5 flex flex-col gap-2 relative overflow-hidden">
      <div className="eyebrow">{label}</div>
      <div
        className={clsx(
          'display text-4xl tabular-nums',
          accent === 'gold' && 'text-accent',
          accent === 'risk' && 'text-risk-critical',
          (!accent || accent === 'navy') && 'text-navy-900',
        )}
      >
        {value}
      </div>
      {delta && (
        <div className="text-xs text-navy-500 mt-1">{delta}</div>
      )}
      <span
        className={clsx(
          'absolute right-0 top-0 h-full w-1',
          accent === 'gold' && 'bg-accent',
          accent === 'risk' && 'bg-risk-critical',
          (!accent || accent === 'navy') && 'bg-navy-700',
        )}
      />
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="card p-5 flex flex-col gap-2">
      <div className="skeleton h-3 w-24" />
      <div className="skeleton h-9 w-28 mt-1" />
      <div className="skeleton h-3 w-16 mt-1" />
    </div>
  );
}

export function RiskPill({ level }: { level: string | null | undefined }) {
  if (!level)
    return (
      <span className="pill border bg-navy-100 text-navy-700 border-navy-200">
        —
      </span>
    );
  return (
    <span className={clsx('pill border capitalize', riskColor(level))}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {level}
    </span>
  );
}

export function UrgencyPill({ urgency }: { urgency: string | null | undefined }) {
  if (!urgency) return null;
  return (
    <span className={clsx('pill capitalize', urgencyColor(urgency))}>
      {urgency}
    </span>
  );
}

export function ScoreBar({ score, label }: { score: number; label?: string }) {
  const color =
    score >= 70 ? 'bg-risk-critical' :
    score >= 50 ? 'bg-risk-high' :
    score >= 30 ? 'bg-risk-medium' :
    'bg-navy-400';
  return (
    <div className="flex items-center gap-3 min-w-[140px]">
      <div className="font-mono text-xs tabular-nums w-7 text-right text-navy-700">{score}</div>
      <div className="flex-1 h-1.5 bg-navy-100 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      {label && <div className="text-[10px] uppercase tracking-wider2 text-navy-400">{label}</div>}
    </div>
  );
}

export function Empty({
  title = 'Nothing here yet',
  description,
  icon: Icon = Inbox,
  action,
}: {
  title?: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  action?: React.ReactNode;
}) {
  return (
    <div className="card p-12 text-center fade-up">
      <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-navy-50 flex items-center justify-center">
        <Icon className="w-5 h-5 text-navy-400" />
      </div>
      <div className="display text-2xl mb-2">{title}</div>
      {description && (
        <p className="text-navy-600 max-w-md mx-auto leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="card p-8 text-center fade-up border-risk-critical/30">
      <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-risk-critical/10 flex items-center justify-center">
        <AlertCircle className="w-5 h-5 text-risk-critical" />
      </div>
      <div className="font-medium text-navy-900 mb-1">Could not load data</div>
      <p className="text-sm text-navy-600 max-w-md mx-auto">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost mt-4 mx-auto">
          <RefreshCw className="w-3.5 h-3.5" />
          Try again
        </button>
      )}
    </div>
  );
}

export function TableSkeleton({ rows = 6, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="bg-navy-50 border-b border-navy-200/60 px-5 py-3 grid gap-6" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="skeleton h-3 w-20" />
        ))}
      </div>
      <div className="divide-y divide-navy-200/40">
        {Array.from({ length: rows }).map((_, r) => (
          <div
            key={r}
            className="px-5 py-4 grid gap-6"
            style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
          >
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="skeleton h-4" style={{ width: `${60 + ((r + c) % 4) * 10}%` }} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="skeleton h-5 w-16" />
            <div className="skeleton h-3 w-24" />
          </div>
          <div className="skeleton h-7 w-3/5 mb-3" />
          <div className="skeleton h-3 w-1/2 mb-2" />
          <div className="skeleton h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}

/** Legacy alias kept for back-compat; prefer the named skeletons above. */
export function Spinner() {
  return (
    <div className="flex items-center justify-center py-12 text-navy-400 text-sm">
      <div className="animate-pulse">Loading…</div>
    </div>
  );
}
