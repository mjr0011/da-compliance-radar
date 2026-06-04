'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { api, setToken, setRefresh, setUser } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // MFA challenge state (second-step)
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      if (res.mfa_required && res.challenge_token) {
        // Two-step flow — prompt for TOTP / backup code
        setChallengeToken(res.challenge_token);
        return;
      }
      if (res.access_token && res.refresh_token && res.user) {
        setToken(res.access_token);
        setRefresh(res.refresh_token);
        setUser(res.user);
        router.push('/dashboard');
      } else {
        setError('Unexpected response from server.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Login failed');
    } finally {
      setBusy(false);
    }
  }

  async function onMfaSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!challengeToken) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.mfaVerify(challengeToken, mfaCode);
      setToken(res.access_token);
      setRefresh(res.refresh_token);
      setUser(res.user);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Verification failed');
    } finally {
      setBusy(false);
    }
  }

  function cancelMfa() {
    setChallengeToken(null);
    setMfaCode('');
    setError(null);
  }

  return (
    <main className="min-h-screen grid lg:grid-cols-5 paper-bg">
      {/* Brand panel */}
      <section className="hidden lg:flex lg:col-span-3 bg-navy-900 text-cream-100 relative overflow-hidden">
        {/* Decorative grid */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #f7f3e9 1px, transparent 1px), linear-gradient(to bottom, #f7f3e9 1px, transparent 1px)',
            backgroundSize: '80px 80px',
          }}
        />
        <div className="relative z-10 flex flex-col justify-between p-16 w-full">
          <div className="flex items-center gap-4">
            <div className="bg-cream-50 px-4 py-2 rounded-sm">
              <Image
                src="/logo.jpg"
                alt="Dennis & Associates"
                width={220}
                height={73}
                priority
              />
            </div>
          </div>

          <div className="max-w-xl">
            <div className="eyebrow text-accent-soft mb-4">Compliance Radar</div>
            <h1 className="display text-5xl xl:text-6xl text-cream-50 mb-6">
              The signal beneath the
              <span className="italic font-light"> noise.</span>
            </h1>
            <p className="text-cream-200/80 text-lg leading-relaxed">
              Continuous monitoring of UK companies. Overdue accounts,
              confirmation statements, strike-off risk, and warm leads —
              scored, classified, and delivered the moment they surface.
            </p>
          </div>

          <div className="flex items-center gap-8 text-xs uppercase tracking-wider2 text-cream-200/60">
            <span>Companies House</span>
            <span className="w-1 h-1 rounded-full bg-accent" />
            <span>AI Classification</span>
            <span className="w-1 h-1 rounded-full bg-accent" />
            <span>Real-time Alerts</span>
          </div>
        </div>
      </section>

      {/* Form panel */}
      <section className="lg:col-span-2 flex items-center justify-center p-8 lg:p-16">
        <div className="w-full max-w-sm">
          <div className="lg:hidden mb-12 flex justify-center">
            <Image src="/logo.jpg" alt="Dennis & Associates" width={260} height={87} priority />
          </div>

          <div className="eyebrow mb-3">Sign in</div>
          <h2 className="display text-3xl mb-10">Compliance Radar</h2>

          {challengeToken ? (
            <form onSubmit={onMfaSubmit} className="space-y-5">
              <div>
                <div className="text-xs text-navy-600 mb-3 leading-relaxed">
                  Enter the 6-digit code from your authenticator app, or one of your
                  8-character backup codes.
                </div>
                <label className="block text-xs font-medium text-navy-600 mb-1.5">
                  Verification code
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  inputMode="text"
                  autoComplete="one-time-code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  className="input text-center font-mono tracking-widest text-lg"
                  placeholder="123 456"
                  maxLength={9}
                />
              </div>

              {error && (
                <div className="text-sm text-risk-critical bg-risk-critical/10 border border-risk-critical/20 rounded-sm px-3 py-2">
                  {error}
                </div>
              )}

              <button type="submit" disabled={busy || mfaCode.length < 6} className="btn-primary w-full">
                {busy ? 'Verifying…' : 'Verify and continue'}
              </button>
              <button type="button" onClick={cancelMfa} className="btn-ghost w-full justify-center text-xs">
                ← Use a different account
              </button>
            </form>
          ) : (
            <form onSubmit={onSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-navy-600 mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  required
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@dennisandassociates.co.uk"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-navy-600 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="••••••••"
                />
              </div>

              {error && (
                <div className="text-sm text-risk-critical bg-risk-critical/10 border border-risk-critical/20 rounded-sm px-3 py-2">
                  {error}
                </div>
              )}

              <button type="submit" disabled={busy} className="btn-primary w-full">
                {busy ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          )}

          <p className="mt-10 text-xs text-navy-500 leading-relaxed">
            First-time setup? Create the admin account from inside the
            backend container:
            <code className="block mt-2 font-mono text-[11px] bg-navy-50 px-2 py-1.5 rounded-sm border border-navy-200/60">
              docker compose exec backend python -m app.scripts.create_admin
            </code>
          </p>
        </div>
      </section>
    </main>
  );
}
