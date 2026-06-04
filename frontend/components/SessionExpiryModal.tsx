'use client';

/**
 * Listens for SESSION_EXPIRED_EVENT dispatched by the API client when an
 * access token has expired and refresh has failed. Pops a modal so the
 * user can re-authenticate without losing the page they were on.
 *
 * The modal is intentionally minimal: email is pre-filled from the
 * stored user, only password is requested. On success we swap in the new
 * tokens silently and dismiss; on failure we route to /login.
 *
 * MFA-enabled accounts can't be re-authed inline (the challenge flow
 * needs more state); for those we just route to /login with a returnTo.
 */

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  SESSION_EXPIRED_EVENT,
  api,
  clearAuth,
  getUser,
  setRefresh,
  setToken,
  setUser,
} from '@/lib/api';
import { Lock, LogOut } from 'lucide-react';

export function SessionExpiryModal() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    function onExpired() {
      // Acknowledge so the API client's fallback redirect doesn't fire
      window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT + ':ack'));
      setOpen(true);
      setError(null);
      setPassword('');
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [open]);

  if (!open) return null;

  const user = getUser();
  const email = user?.email || '';

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) {
      goToLogin();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      if (res.mfa_required) {
        // Inline re-auth can't drive an MFA challenge flow — bounce to /login
        clearAuth();
        router.replace('/login');
        return;
      }
      if (res.access_token && res.refresh_token && res.user) {
        setToken(res.access_token);
        setRefresh(res.refresh_token);
        setUser(res.user);
        setOpen(false);
      } else {
        setError('Unexpected response from server.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  }

  function goToLogin() {
    clearAuth();
    setOpen(false);
    router.replace('/login');
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-navy-900/60 backdrop-blur-sm flex items-center justify-center p-4 fade-up"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-expiry-title"
    >
      <div ref={dialogRef} tabIndex={-1} className="card max-w-md w-full p-7 focus:outline-none">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-accent/15 flex items-center justify-center">
            <Lock className="w-4 h-4 text-accent" />
          </div>
          <div>
            <div className="eyebrow">Session expired</div>
            <h2 id="session-expiry-title" className="display text-xl text-navy-900 mt-0.5">
              Sign in to continue
            </h2>
          </div>
        </div>

        <p className="text-sm text-navy-600 leading-relaxed mb-5">
          For your security, your session has timed out. Re-enter your password
          and we'll pick up where you left off — no need to navigate back.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Email
            </label>
            <input value={email} readOnly className="input bg-cream-100/60 text-navy-600" />
          </div>
          <div className="mb-4">
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Password
            </label>
            <input
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              required
            />
          </div>

          {error && (
            <div className="text-xs text-risk-critical mb-3" role="alert">
              {error}
            </div>
          )}

          <div className="flex items-center justify-between gap-3 mt-6">
            <button
              type="button"
              onClick={goToLogin}
              className="btn-ghost text-xs"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign in differently
            </button>
            <button type="submit" disabled={busy || !password} className="btn-primary">
              {busy ? 'Signing in…' : 'Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
