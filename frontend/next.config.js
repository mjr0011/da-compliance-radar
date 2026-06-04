/** @type {import('next').NextConfig} */

/**
 * Security headers applied to every response.
 *
 * Notes on choices:
 * - CSP allows 'unsafe-inline' for styles because Tailwind's runtime + Next.js
 *   inject inline styles. 'unsafe-inline' for scripts is also required by
 *   Next's hydration shim; switching to a strict-dynamic + nonce policy is
 *   the next step but needs a custom middleware.
 * - 'unsafe-eval' is needed for Next.js dev tooling but should be removed
 *   in production builds — gated on NODE_ENV below.
 * - connect-src allows the same-origin + the backend API URL (set via env).
 * - img-src includes data: and https: to support the QR-code image-server
 *   fallback in /admin/mfa.
 * - frame-ancestors 'none' is the modern replacement for X-Frame-Options DENY;
 *   both are sent for broader compatibility.
 */
const API_HOST = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const isDev = process.env.NODE_ENV !== 'production';

const CSP_DIRECTIVES = [
  `default-src 'self'`,
  // Next's hydration + Tailwind currently require inline. Dev also needs eval.
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
  `style-src 'self' 'unsafe-inline'`,
  `img-src 'self' data: blob: https:`,
  `font-src 'self' data:`,
  // Same-origin + the backend host (and websocket variant for HMR in dev)
  `connect-src 'self' ${API_HOST}${isDev ? ' ws://localhost:* http://localhost:*' : ''}`,
  `frame-ancestors 'none'`,
  `base-uri 'self'`,
  `form-action 'self'`,
  `object-src 'none'`,
];

const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: CSP_DIRECTIVES.join('; '),
  },
  {
    // Force HTTPS for 2 years; include subdomains; signal preload eligibility.
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin',
  },
  {
    // Disable anything we don't actively use; opt back in per-feature.
    key: 'Permissions-Policy',
    value:
      'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
  },
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on',
  },
];

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [
      // QR-server is used as a fallback for the MFA enrollment QR; if you
      // bundle a client-side QR renderer (qrcode.react or qrcode-generator),
      // drop this entry.
      { protocol: 'https', hostname: 'api.qrserver.com' },
    ],
  },
  async headers() {
    return [
      {
        // Match every route, including assets — HSTS in particular has to
        // be present on the first byte the browser ever sees.
        source: '/(.*)',
        headers: securityHeaders,
      },
    ];
  },
};

module.exports = nextConfig;
