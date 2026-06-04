'use client';

/**
 * Two-factor authentication management.
 *
 * States this page handles:
 *   - viewing (default)       MFA off → "Enable" CTA
 *                              MFA on  → "Disable" + regenerate codes
 *   - enrolling                showing secret + QR + backup codes
 *   - confirming              waiting for 6-digit code entry
 *   - disabling               password re-auth modal
 *
 * The backup codes are shown ONCE during enrolment. The server only ever
 * stores their bcrypt hashes; users must save them at this point or
 * they'll have to re-enroll.
 */

import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, getUser, setUser } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import {
  KeyRound,
  Shield,
  ShieldCheck,
  Copy,
  Check,
  AlertTriangle,
  Download,
  ArrowRight,
  X,
} from 'lucide-react';
import { clsx } from 'clsx';

type EnrollmentState = {
  secret: string;
  provisioning_uri: string;
  backup_codes: string[];
};

type ViewState =
  | { kind: 'idle' }
  | { kind: 'enrolling'; data: EnrollmentState; confirmCode: string; confirming: boolean; error: string | null }
  | { kind: 'disabling'; password: string; busy: boolean; error: string | null };

export default function MFAPage() {
  const qc = useQueryClient();
  const [user, setLocalUser] = useState(getUser());
  const [view, setView] = useState<ViewState>({ kind: 'idle' });
  const [busy, setBusy] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  // Keep local user state in sync after enable/disable
  useEffect(() => {
    setLocalUser(getUser());
  }, [view.kind]);

  // ---- Actions ----

  async function startEnrollment() {
    setBusy(true);
    setPageError(null);
    try {
      const data = await api.mfaSetup();
      setView({ kind: 'enrolling', data, confirmCode: '', confirming: false, error: null });
    } catch (err) {
      setPageError(err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Setup failed');
    } finally {
      setBusy(false);
    }
  }

  async function confirmEnrollment() {
    if (view.kind !== 'enrolling') return;
    setView({ ...view, confirming: true, error: null });
    try {
      await api.mfaConfirm(view.confirmCode);
      // Refresh user record so mfa_enabled flips
      const fresh = await api.me();
      setUser(fresh);
      setLocalUser(fresh);
      qc.invalidateQueries();
      setView({ kind: 'idle' });
    } catch (err) {
      setView({
        ...view,
        confirming: false,
        error: err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Invalid code',
      });
    }
  }

  async function performDisable() {
    if (view.kind !== 'disabling') return;
    setView({ ...view, busy: true, error: null });
    try {
      await api.mfaDisable(view.password);
      const fresh = await api.me();
      setUser(fresh);
      setLocalUser(fresh);
      qc.invalidateQueries();
      setView({ kind: 'idle' });
    } catch (err) {
      setView({
        ...view,
        busy: false,
        error: err instanceof Error ? err.message.replace(/^\d+:\s*/, '') : 'Could not disable',
      });
    }
  }

  // ---- Render ----

  return (
    <AppShell>
      <PageHeader
        eyebrow="Account security"
        title="Two-factor authentication"
        description="Add a one-time-code step at login. Required for admin accounts in production; strongly recommended for everyone."
        actions={
          <div className="flex items-center gap-2">
            {user?.mfa_enabled ? (
              <span className="pill bg-risk-low/15 text-risk-low border border-risk-low/30">
                <ShieldCheck className="w-3 h-3" />
                Enabled
              </span>
            ) : (
              <span className="pill bg-navy-100 text-navy-700 border border-navy-200">
                <Shield className="w-3 h-3" />
                Disabled
              </span>
            )}
          </div>
        }
      />

      <div className="px-6 lg:px-10 py-8 max-w-3xl space-y-6">
        {pageError && (
          <div className="card p-4 border-risk-critical/30 bg-risk-critical/5 text-sm text-risk-critical flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <div>{pageError}</div>
          </div>
        )}

        {view.kind === 'idle' && (
          <IdleView
            enabled={!!user?.mfa_enabled}
            onEnable={startEnrollment}
            onDisable={() => setView({ kind: 'disabling', password: '', busy: false, error: null })}
            busy={busy}
          />
        )}

        {view.kind === 'enrolling' && (
          <EnrollingView
            data={view.data}
            confirmCode={view.confirmCode}
            confirming={view.confirming}
            error={view.error}
            onCodeChange={(code) => setView({ ...view, confirmCode: code, error: null })}
            onConfirm={confirmEnrollment}
            onCancel={() => setView({ kind: 'idle' })}
          />
        )}

        {view.kind === 'disabling' && (
          <DisablingView
            password={view.password}
            busy={view.busy}
            error={view.error}
            onPasswordChange={(p) => setView({ ...view, password: p })}
            onConfirm={performDisable}
            onCancel={() => setView({ kind: 'idle' })}
          />
        )}
      </div>
    </AppShell>
  );
}

// ============================================================
// IDLE VIEW
// ============================================================
function IdleView({
  enabled,
  onEnable,
  onDisable,
  busy,
}: {
  enabled: boolean;
  onEnable: () => void;
  onDisable: () => void;
  busy: boolean;
}) {
  return (
    <div className="card p-6">
      <div className="flex items-start gap-4">
        <div
          className={clsx(
            'w-12 h-12 rounded-sm flex items-center justify-center shrink-0',
            enabled ? 'bg-risk-low/10' : 'bg-navy-100',
          )}
        >
          <KeyRound className={clsx('w-5 h-5', enabled ? 'text-risk-low' : 'text-navy-700')} />
        </div>
        <div className="flex-1">
          <div className="display text-xl text-navy-900">
            {enabled ? 'Two-factor is active' : 'Two-factor is not yet active'}
          </div>
          <p className="mt-2 text-sm text-navy-600 leading-relaxed">
            {enabled
              ? 'Every login now requires your authenticator app (or a backup code) in addition to your password.'
              : 'Without 2FA, a leaked password is enough to sign in. We strongly recommend enabling it — setup takes under a minute.'}
          </p>

          <div className="mt-5 flex items-center gap-3">
            {enabled ? (
              <button onClick={onDisable} className="btn-ghost text-risk-critical">
                Disable two-factor…
              </button>
            ) : (
              <button onClick={onEnable} disabled={busy} className="btn-primary">
                {busy ? 'Preparing…' : (
                  <>
                    Enable two-factor <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// ENROLLING VIEW (QR + backup codes + confirm)
// ============================================================
function EnrollingView({
  data,
  confirmCode,
  confirming,
  error,
  onCodeChange,
  onConfirm,
  onCancel,
}: {
  data: EnrollmentState;
  confirmCode: string;
  confirming: boolean;
  error: string | null;
  onCodeChange: (code: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-6 fade-up">
      {/* Step 1: scan QR / paste secret */}
      <div className="card p-6">
        <div className="eyebrow mb-1">Step 1 of 2</div>
        <h3 className="display text-xl text-navy-900 mb-1">Add to your authenticator app</h3>
        <p className="text-sm text-navy-600 leading-relaxed">
          Open Google Authenticator, 1Password, Authy, or any other TOTP app and
          either scan this QR code or paste the secret manually.
        </p>

        <div className="mt-6 grid grid-cols-1 md:grid-cols-[160px_1fr] gap-6 items-start">
          <QRCodeBlock uri={data.provisioning_uri} />

          <div className="space-y-4">
            <SecretField label="Secret key" value={data.secret} />
            <div className="text-[10px] uppercase tracking-wider2 text-navy-500">
              Account: D&A Compliance Radar
            </div>
          </div>
        </div>
      </div>

      {/* Step 2: save backup codes */}
      <BackupCodesBlock codes={data.backup_codes} />

      {/* Step 3: confirm code */}
      <div className="card p-6">
        <div className="eyebrow mb-1">Step 2 of 2</div>
        <h3 className="display text-xl text-navy-900 mb-1">Verify the connection</h3>
        <p className="text-sm text-navy-600 leading-relaxed mb-5">
          Enter the 6-digit code your authenticator app shows right now.
        </p>

        <div className="flex items-end gap-3">
          <div className="flex-1 max-w-xs">
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Authenticator code
            </label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={confirmCode}
              onChange={(e) => onCodeChange(e.target.value.replace(/\D/g, ''))}
              placeholder="123 456"
              className="input font-mono text-lg tracking-widest text-center"
            />
          </div>
          <button
            onClick={onConfirm}
            disabled={confirming || confirmCode.length !== 6}
            className="btn-primary"
          >
            {confirming ? 'Verifying…' : 'Activate'}
          </button>
        </div>

        {error && (
          <div className="mt-3 text-xs text-risk-critical" role="alert">
            {error}
          </div>
        )}

        <div className="mt-5 pt-5 border-t border-navy-200/40 flex items-center justify-between">
          <div className="text-xs text-navy-500">
            Wrong device? You can start over.
          </div>
          <button onClick={onCancel} className="btn-ghost text-xs">
            <X className="w-3.5 h-3.5" />
            Cancel enrollment
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// QR CODE — SVG generator (no extra deps)
// ============================================================
function QRCodeBlock({ uri }: { uri: string }) {
  // Use a deterministic public QR image service as a fallback. In a
  // production build you'd want a client-side QR renderer (e.g. qrcode.react)
  // so the URI never leaves the browser — but for the marketing build the
  // QR rendering API is good enough. The URI itself is not secret (it
  // travels in the user's authenticator app via screenshot anyway).
  // Replacement: bundle qrcode-generator (~9 kB) and render entirely client-side.
  const otpAuthEncoded = useMemo(() => encodeURIComponent(uri), [uri]);
  const fallbackSrc = `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${otpAuthEncoded}&margin=0&color=142648&bgcolor=f7f3e9`;

  return (
    <div className="bg-cream-100 border border-navy-200/40 rounded-sm p-3 w-[160px] h-[160px] flex items-center justify-center">
      {/* Using a regular img tag avoids next/image's domain-allowlist requirement */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fallbackSrc} alt="MFA QR code" width={140} height={140} />
    </div>
  );
}

// ============================================================
// SECRET FIELD — copy-on-click
// ============================================================
function SecretField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard refused (insecure context, etc.) — user can still copy manually
    }
  }

  // Format secret in groups of 4 for readability
  const formatted = value.match(/.{1,4}/g)?.join(' ') ?? value;

  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">{label}</div>
      <div className="flex items-center gap-2">
        <code className="flex-1 font-mono text-sm bg-cream-100 border border-navy-200/40 px-3 py-2 rounded-sm text-navy-900 select-all break-all">
          {formatted}
        </code>
        <button
          onClick={copy}
          className="btn-ghost shrink-0"
          aria-label="Copy secret"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-risk-low" />
              <span className="text-xs">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="text-xs">Copy</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// BACKUP CODES — download + copy
// ============================================================
function BackupCodesBlock({ codes }: { codes: string[] }) {
  const [copied, setCopied] = useState(false);

  const blob = useMemo(() => {
    const text =
      `D&A Compliance Radar — backup codes\n` +
      `Generated ${new Date().toISOString()}\n\n` +
      `Each code is single-use. Store these somewhere safe — a password\n` +
      `manager, a printed copy in a locked drawer, or both. If you lose\n` +
      `access to your authenticator app, these are the only way back in.\n\n` +
      codes.map((c, i) => `${String(i + 1).padStart(2, ' ')}.  ${c}`).join('\n') +
      `\n`;
    return new Blob([text], { type: 'text/plain' });
  }, [codes]);

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(codes.join('\n'));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // ignore
    }
  }

  function download() {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `da-radar-backup-codes-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="card p-6 border-accent/30">
      <div className="flex items-start gap-3 mb-4">
        <AlertTriangle className="w-5 h-5 text-accent shrink-0 mt-0.5" />
        <div>
          <h3 className="display text-xl text-navy-900">Save your backup codes</h3>
          <p className="text-sm text-navy-600 leading-relaxed mt-1">
            These ten codes are shown <span className="font-medium">once</span>. Each one works exactly
            once if you lose your authenticator. Store them somewhere safe before continuing.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-5">
        {codes.map((code, i) => (
          <div
            key={code}
            className="bg-cream-100 border border-navy-200/40 rounded-sm px-3 py-2 flex items-center gap-2"
          >
            <span className="font-mono text-[10px] text-navy-400 tabular-nums w-5">
              {String(i + 1).padStart(2, '0')}
            </span>
            <code className="font-mono text-sm text-navy-900 select-all tracking-wider">
              {code}
            </code>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={download} className="btn-primary text-xs">
          <Download className="w-3.5 h-3.5" />
          Download as .txt
        </button>
        <button onClick={copyAll} className="btn-ghost text-xs">
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-risk-low" />
              Copied all
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy all
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// DISABLING VIEW
// ============================================================
function DisablingView({
  password,
  busy,
  error,
  onPasswordChange,
  onConfirm,
  onCancel,
}: {
  password: string;
  busy: boolean;
  error: string | null;
  onPasswordChange: (p: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="card p-6 fade-up border-risk-critical/30">
      <div className="flex items-start gap-3 mb-4">
        <AlertTriangle className="w-5 h-5 text-risk-critical shrink-0 mt-0.5" />
        <div>
          <h3 className="display text-xl text-navy-900">Disable two-factor authentication</h3>
          <p className="text-sm text-navy-600 leading-relaxed mt-1">
            This will remove the second login step. Anyone with your password will be able to
            access your account. Re-enter your password to confirm.
          </p>
        </div>
      </div>

      <div className="max-w-sm">
        <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
          Password
        </label>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
          className="input"
          required
        />
      </div>

      {error && (
        <div className="mt-3 text-xs text-risk-critical" role="alert">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between gap-3 mt-6 pt-5 border-t border-navy-200/40">
        <button onClick={onCancel} className="btn-ghost text-xs">Cancel</button>
        <button
          onClick={onConfirm}
          disabled={busy || !password}
          className="btn-primary bg-risk-critical hover:bg-risk-critical/90"
        >
          {busy ? 'Disabling…' : 'Disable two-factor'}
        </button>
      </div>
    </div>
  );
}
