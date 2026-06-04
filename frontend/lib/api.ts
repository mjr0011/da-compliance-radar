/**
 * Typed API client for the FastAPI backend.
 *
 * Auth flow:
 * - Login returns access_token (short-lived) + refresh_token (30 days)
 * - Access token attached to every request
 * - On 401, attempt one silent refresh and retry the original request
 * - If refresh fails, clear auth and redirect to /login
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const TOKEN_KEY = 'da_radar_token';
export const REFRESH_KEY = 'da_radar_refresh';
export const USER_KEY = 'da_radar_user';

export type User = {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'manager' | 'viewer';
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
};

export type Compliance = {
  accounts_due_date: string | null;
  accounts_overdue: boolean;
  confirmation_due_date: string | null;
  confirmation_overdue: boolean;
  strike_off_warning: boolean;
  in_insolvency: boolean;
  next_deadline: string | null;
  days_until_next_deadline: number | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
};

export type Company = {
  id: number;
  company_number: string;
  company_name: string;
  status: string | null;
  sic_code: string | null;
  sic_description: string | null;
  incorporation_date: string | null;
  locality: string | null;
  postal_code: string | null;
  website: string | null;
  phone: string | null;
  primary_email: string | null;
  lead_score: number;
  risk_score: number;
  created_at: string;
  updated_at: string;
  compliance: Compliance | null;
};

export type Lead = {
  id: number;
  company_id: number;
  source: string;
  lead_type: string;
  summary: string | null;
  ai_category: string | null;
  urgency: 'low' | 'medium' | 'high' | 'urgent';
  estimated_value_gbp: number | null;
  lead_score: number;
  status: string;
  assigned_to_id: number | null;
  crm_provider: string | null;
  crm_external_id: string | null;
  crm_synced_at: string | null;
  created_at: string;
  updated_at: string;
  company: Company | null;
};

export type Alert = {
  id: number;
  lead_id: number | null;
  alert_channel: string;
  alert_type: string;
  sent_status: 'pending' | 'sent' | 'failed';
  sent_at: string | null;
  error_message: string | null;
  created_at: string;
};

export type DashboardStats = {
  total_companies_tracked: number;
  overdue_accounts_count: number;
  overdue_confirmation_count: number;
  strike_off_warnings: number;
  high_risk_companies: number;
  new_leads_7d: number;
  high_value_leads: number;
  alerts_sent_24h: number;
};

export type SectorBreakdown = {
  sic_description: string;
  count: number;
  avg_lead_score: number;
};

export type DashboardResponse = {
  stats: DashboardStats;
  top_sectors: SectorBreakdown[];
};

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditLogEntry = {
  id: number;
  event_type: string;
  actor_id: number | null;
  actor_email: string | null;
  actor_ip: string | null;
  actor_user_agent: string | null;
  target_type: string | null;
  target_id: number | null;
  detail: Record<string, unknown> | null;
  created_at: string;
};

export type SuppressionEntry = {
  id: number;
  company_number: string | null;
  email: string | null;
  domain: string | null;
  source: string;
  lawful_basis: string | null;
  reason: string | null;
  added_by: string | null;
  request_received_at: string | null;
  created_at: string;
};

// --- Token helpers ---

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function getRefresh(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setRefresh(t: string) {
  localStorage.setItem(REFRESH_KEY, t);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getUser(): User | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setUser(u: User) {
  localStorage.setItem(USER_KEY, JSON.stringify(u));
}

// --- Refresh management ---
// Single in-flight refresh so concurrent 401s don't trigger N refresh calls.

let refreshInFlight: Promise<string | null> | null = null;

async function attemptRefresh(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  const refresh = getRefresh();
  if (!refresh) return null;

  refreshInFlight = (async () => {
    try {
      const r = await fetch(`${API_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!r.ok) return null;
      const data = await r.json();
      setToken(data.access_token);
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/**
 * Dispatched by the API client when the access token has expired AND
 * refresh has failed. The AppShell listens for this and shows a modal
 * giving the user a chance to re-authenticate without losing context.
 * If the listener isn't mounted (e.g. on the homepage), the auth state
 * is cleared and the user is redirected to /login.
 */
export const SESSION_EXPIRED_EVENT = 'da-radar:session-expired';

function dispatchSessionExpired() {
  if (typeof window === 'undefined') return;
  // Detail flag lets the modal-listener know to handle this; the
  // fallback below clears auth + redirects after a short grace period
  // so any listener has time to run.
  let handled = false;
  const handler = () => { handled = true; };
  window.addEventListener(SESSION_EXPIRED_EVENT + ':ack', handler, { once: true });
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));

  // Fallback: if no listener acknowledged within 200ms, redirect.
  setTimeout(() => {
    if (handled) return;
    clearAuth();
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
  }, 200);
}

// --- Core fetcher ---

async function http<T>(
  path: string,
  init: RequestInit = {},
  _retried = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) || {}),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const r = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (r.status === 401 && !_retried) {
    const newToken = await attemptRefresh();
    if (newToken) {
      return http<T>(path, init, true);
    }
    dispatchSessionExpired();
  }

  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try { detail = JSON.parse(text).detail || text; } catch {}
    throw new Error(`${r.status}: ${detail}`);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

function qs(params: Record<string, string | number | boolean | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== false) q.set(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : '';
}

export type LoginResponse = {
  mfa_required: boolean;
  access_token?: string | null;
  refresh_token?: string | null;
  challenge_token?: string | null;
  user?: User | null;
};

export type MFASetupResponse = {
  secret: string;
  provisioning_uri: string;
  backup_codes: string[];
};

export type AnalyticsResponse = {
  leads_by_status: Record<string, number>;
  leads_by_urgency: Record<string, number>;
  alerts_by_channel: Record<string, Record<string, number>>;
  audit_events_30d: { event_type: string; count: number }[];
  risk_distribution: Record<string, number>;
  pipeline_value_gbp: number;
};

// --- Endpoints ---

export const api = {
  // auth
  login: (email: string, password: string) =>
    http<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  mfaVerify: (challenge_token: string, code: string) =>
    http<{ access_token: string; refresh_token: string; user: User }>(
      '/api/auth/mfa/verify',
      { method: 'POST', body: JSON.stringify({ challenge_token, code }) },
    ),
  mfaSetup: () =>
    http<MFASetupResponse>('/api/auth/mfa/setup', { method: 'POST' }),
  mfaConfirm: (code: string) =>
    http<void>('/api/auth/mfa/confirm', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
  mfaDisable: (password: string) =>
    http<void>('/api/auth/mfa/disable', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
  logout: () => http<void>('/api/auth/logout', { method: 'POST' }),
  me: () => http<User>('/api/auth/me'),

  // dashboard
  dashboard: () => http<DashboardResponse>('/api/dashboard'),

  // companies
  listCompanies: (params: Record<string, string | number | boolean | undefined> = {}) =>
    http<Paginated<Company>>(`/api/companies${qs(params)}`),
  getCompany: (n: string) => http<Company>(`/api/companies/${n}`),
  refreshCompany: (n: string) =>
    http<{ queued: boolean }>(`/api/companies/${n}/refresh`, { method: 'POST' }),

  // leads
  listLeads: (params: Record<string, string | number | undefined> = {}) =>
    http<Paginated<Lead>>(`/api/leads${qs(params)}`),
  updateLead: (id: number, body: Partial<{ status: string; notes: string; assigned_to_id: number }>) =>
    http<Lead>(`/api/leads/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  syncLeadCrm: (id: number) =>
    http<{ queued: boolean }>(`/api/leads/${id}/sync-crm`, { method: 'POST' }),
  fireLeadAlert: (id: number) =>
    http<{ queued: boolean }>(`/api/leads/${id}/alert`, { method: 'POST' }),

  // alerts
  listAlerts: (params: Record<string, string | undefined> = {}) =>
    http<Alert[]>(`/api/alerts${qs(params)}`),

  // admin
  listAuditLog: (params: Record<string, string | number | undefined> = {}) =>
    http<Paginated<AuditLogEntry>>(`/api/admin/audit-log${qs(params)}`),
  listSuppression: (params: Record<string, string | number | undefined> = {}) =>
    http<Paginated<SuppressionEntry>>(`/api/admin/suppression${qs(params)}`),
  addSuppression: (body: Partial<SuppressionEntry>) =>
    http<SuppressionEntry>('/api/admin/suppression', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteSuppression: (id: number) =>
    http<void>(`/api/admin/suppression/${id}`, { method: 'DELETE' }),
  analytics: () => http<AnalyticsResponse>('/api/admin/analytics'),
};
