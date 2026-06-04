'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import {
  LayoutDashboard,
  Building2,
  Sparkles,
  BellRing,
  LogOut,
  Radar,
  Shield,
  ScrollText,
  BarChart3,
  KeyRound,
  Menu,
  X,
} from 'lucide-react';
import { api, clearAuth, getToken, getUser, User } from '@/lib/api';
import { SessionExpiryModal } from '@/components/SessionExpiryModal';

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: string[];
  section?: string;
};

const NAV: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/companies', label: 'Companies', icon: Building2 },
  { href: '/leads', label: 'Leads', icon: Sparkles },
  { href: '/alerts', label: 'Alerts', icon: BellRing },
  {
    href: '/admin/analytics',
    label: 'Analytics',
    icon: BarChart3,
    roles: ['admin', 'manager'],
    section: 'Admin',
  },
  {
    href: '/admin/audit-log',
    label: 'Audit log',
    icon: ScrollText,
    roles: ['admin'],
    section: 'Admin',
  },
  {
    href: '/admin/suppression',
    label: 'Suppression',
    icon: Shield,
    roles: ['admin', 'manager'],
    section: 'Admin',
  },
  {
    href: '/admin/mfa',
    label: 'Two-factor auth',
    icon: KeyRound,
    section: 'Account',
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUserState] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    setUserState(getUser());
    setReady(true);
  }, [router]);

  // Close mobile drawer on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  async function logout() {
    try { await api.logout(); } catch { /* best-effort */ }
    clearAuth();
    router.replace('/login');
  }

  if (!ready) {
    return (
      <main className="min-h-screen flex items-center justify-center paper-bg">
        <div className="flex items-center gap-3 text-navy-500 text-sm">
          <Radar className="w-4 h-4 animate-pulse" />
          <span className="tracking-wider2 uppercase text-xs">Loading…</span>
        </div>
      </main>
    );
  }

  const visibleNav = NAV.filter(
    (n) => !n.roles || (user && n.roles.includes(user.role)),
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr] paper-bg">
      {/* Mobile top bar */}
      <header className="lg:hidden sticky top-0 z-30 bg-navy-900 text-cream-50 px-4 py-3 flex items-center justify-between border-b border-navy-800">
        <div className="bg-cream-50 px-2 py-1 rounded-sm">
          <Image src="/logo.jpg" alt="Dennis & Associates" width={120} height={40} priority />
        </div>
        <button
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          className="p-2 -mr-2"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Sidebar — desktop persistent, mobile drawer */}
      <aside
        className={`bg-navy-900 text-cream-100 flex-col border-r border-navy-800
          fixed inset-y-0 left-0 w-[280px] z-40 transform transition-transform
          lg:static lg:translate-x-0 lg:flex
          ${mobileOpen ? 'flex translate-x-0' : 'hidden -translate-x-full lg:flex'}`}
      >
        <div className="px-5 pt-6 pb-8 border-b border-navy-800/60">
          <div className="bg-cream-50 px-3 py-2 rounded-sm inline-block">
            <Image
              src="/logo.jpg"
              alt="Dennis & Associates"
              width={180}
              height={60}
              priority
            />
          </div>
          <div className="mt-4 flex items-center gap-2 text-[11px] uppercase tracking-wider2 text-accent-soft">
            <Radar className="w-3.5 h-3.5" />
            <span>Compliance Radar</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {visibleNav.map((item, idx) => {
            const showSectionHeader =
              item.section && (idx === 0 || visibleNav[idx - 1].section !== item.section);
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <div key={item.href}>
                {showSectionHeader && (
                  <div className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider2 text-cream-200/40 font-medium">
                    {item.section}
                  </div>
                )}
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 text-sm rounded-sm transition ${
                    active
                      ? 'bg-cream-50/10 text-cream-50 font-medium'
                      : 'text-cream-100/60 hover:text-cream-50 hover:bg-cream-50/5'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.label}</span>
                </Link>
              </div>
            );
          })}
        </nav>

        <div className="px-3 py-4 border-t border-navy-800/60">
          {user && (
            <div className="px-3 mb-3">
              <div className="text-sm font-medium text-cream-50 truncate">{user.name}</div>
              <div className="text-[11px] text-cream-200/60 uppercase tracking-wider2">
                {user.role}
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 px-3 py-2 text-sm rounded-sm text-cream-100/60 hover:text-cream-50 hover:bg-cream-50/5 transition"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
          className="lg:hidden fixed inset-0 bg-navy-900/50 z-30"
        />
      )}

      <main className="overflow-x-hidden">{children}</main>

      <SessionExpiryModal />
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="px-6 lg:px-10 pt-8 lg:pt-10 pb-6 lg:pb-8 border-b border-navy-200/40 fade-up">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 lg:gap-6">
        <div className="max-w-3xl">
          {eyebrow && <div className="eyebrow mb-3">{eyebrow}</div>}
          <h1 className="display text-3xl lg:text-4xl">{title}</h1>
          {description && (
            <p className="mt-3 text-navy-600 leading-relaxed max-w-2xl text-sm lg:text-base">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
      </div>
    </header>
  );
}
