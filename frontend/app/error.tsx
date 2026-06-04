'use client';

/**
 * Route-level error boundary.
 *
 * Catches any thrown error during render or in event handlers within
 * the `app/` tree. The framework re-renders this component with the
 * error and a `reset()` to retry the failed render.
 *
 * Keep this branded and calm — a crash is bad enough; an apologetic
 * Sentry-bug-report URL is worse.
 */

import { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production this hands the error to Sentry (initialised in main.py
    // for the API side; on the frontend you'd add @sentry/nextjs and it
    // wires in here automatically). For now we just log.
    // eslint-disable-next-line no-console
    console.error('Route error:', error);
  }, [error]);

  return (
    <main className="min-h-screen flex items-center justify-center paper-bg px-6">
      <div className="card max-w-lg w-full p-8 text-center fade-up">
        <div className="w-12 h-12 mx-auto mb-5 rounded-full bg-risk-critical/10 flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-risk-critical" />
        </div>
        <div className="eyebrow mb-3">Something broke</div>
        <h1 className="display text-2xl text-navy-900 mb-3">
          This page hit an unexpected error.
        </h1>
        <p className="text-sm text-navy-600 leading-relaxed mb-6">
          The error has been logged. You can try again, or head back to the dashboard.
          If this keeps happening, please contact your administrator.
        </p>

        {error.digest && (
          <div className="font-mono text-[10px] text-navy-400 mb-6">
            ref: {error.digest}
          </div>
        )}

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <button onClick={() => reset()} className="btn-primary">
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </button>
          <Link href="/dashboard" className="btn-ghost">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
