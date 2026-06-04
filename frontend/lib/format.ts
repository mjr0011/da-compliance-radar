export function formatGBP(n: number | null | undefined): string {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.round((d - now) / 1000);
  const abs = Math.abs(diff);
  const sign = diff < 0 ? -1 : 1;
  const fmt = new Intl.RelativeTimeFormat('en-GB', { numeric: 'auto' });
  if (abs < 60) return fmt.format(sign * abs, 'second');
  if (abs < 3600) return fmt.format(Math.round((sign * abs) / 60), 'minute');
  if (abs < 86400) return fmt.format(Math.round((sign * abs) / 3600), 'hour');
  if (abs < 2592000) return fmt.format(Math.round((sign * abs) / 86400), 'day');
  if (abs < 31536000) return fmt.format(Math.round((sign * abs) / 2592000), 'month');
  return fmt.format(Math.round((sign * abs) / 31536000), 'year');
}

export function riskColor(level: string | null | undefined): string {
  switch (level) {
    case 'critical':
      return 'bg-risk-critical/10 text-risk-critical border-risk-critical/30';
    case 'high':
      return 'bg-risk-high/10 text-risk-high border-risk-high/30';
    case 'medium':
      return 'bg-risk-medium/10 text-risk-medium border-risk-medium/30';
    case 'low':
      return 'bg-risk-low/10 text-risk-low border-risk-low/30';
    default:
      return 'bg-navy-100 text-navy-700 border-navy-200';
  }
}

export function urgencyColor(u: string | null | undefined): string {
  switch (u) {
    case 'urgent':
      return 'bg-risk-critical text-white';
    case 'high':
      return 'bg-risk-high text-white';
    case 'medium':
      return 'bg-risk-medium text-white';
    case 'low':
      return 'bg-navy-200 text-navy-800';
    default:
      return 'bg-navy-200 text-navy-800';
  }
}
