'use client';

/**
 * Global error boundary — Next.js App Router uses this only when the
 * root layout itself crashes (i.e. the normal error.tsx couldn't render
 * because the app shell is broken). Must include its own <html> + <body>
 * because the root layout failed to render them.
 */

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error('Global error:', error);
  }, [error]);

  return (
    <html lang="en">
      <body style={{
        margin: 0,
        fontFamily: 'Inter, system-ui, sans-serif',
        background: '#f7f3e9',
        color: '#142648',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}>
        <div style={{
          maxWidth: 480,
          width: '100%',
          background: '#ffffff',
          border: '1px solid rgba(20, 38, 72, 0.15)',
          borderRadius: 4,
          padding: '32px',
          textAlign: 'center',
          boxShadow: '0 4px 16px -8px rgba(20, 38, 72, 0.2)',
        }}>
          <div style={{
            fontSize: 11,
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            color: '#7a8197',
            marginBottom: 12,
          }}>Critical error</div>

          <h1 style={{
            fontFamily: '"Bodoni Moda", Georgia, serif',
            fontSize: 28,
            margin: '0 0 12px',
            lineHeight: 1.05,
          }}>
            The application failed to load.
          </h1>

          <p style={{ fontSize: 14, color: '#3d4866', lineHeight: 1.6, marginBottom: 24 }}>
            We've logged the error. Try refreshing — if that doesn't work,
            please contact your administrator.
          </p>

          {error.digest && (
            <div style={{
              fontFamily: 'JetBrains Mono, ui-monospace, monospace',
              fontSize: 10,
              color: '#7a8197',
              marginBottom: 24,
            }}>
              ref: {error.digest}
            </div>
          )}

          <button
            onClick={() => reset()}
            style={{
              background: '#142648',
              color: '#f7f3e9',
              border: 'none',
              padding: '10px 20px',
              fontSize: 14,
              fontWeight: 500,
              cursor: 'pointer',
              borderRadius: 4,
            }}
          >
            Reload the application
          </button>
        </div>
      </body>
    </html>
  );
}
