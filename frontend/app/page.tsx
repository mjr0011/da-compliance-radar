'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  Radar,
  Building2,
  Sparkles,
  Shield,
  Cpu,
  CheckCircle2,
  HardHat,
  Home,
  ShoppingBag,
  Heart,
  Briefcase,
  Rocket,
  Database,
  Lock,
  ScrollText,
  KeyRound,
  Cloud,
  BadgeCheck,
  Bell,
  Cloud as CloudIcon,
} from 'lucide-react';
import { getToken } from '@/lib/api';
import { HeroDashboard } from '@/components/marketing/HeroDashboard';
import { DashboardShowcase } from '@/components/marketing/DashboardShowcase';
import { TickerBar } from '@/components/marketing/TickerBar';
import { useCountUp, useReveal } from '@/lib/hooks';

export default function HomePage() {
  const [authed, setAuthed] = useState(false);
  useEffect(() => { setAuthed(!!getToken()); }, []);

  return (
    <main className="bg-cream-50 text-navy-900 min-h-screen overflow-x-hidden">
      <Header authed={authed} />
      <TickerBar />
      <Hero />
      <AnimatedStats />
      <TrustStrip />
      <DashboardShowcaseSection />
      <IntelligenceFeatures />
      <TargetIndustries />
      <ProductScreenshots />
      <SecuritySection />
      <Pricing />
      <FooterCTA authed={authed} />
      <Footer />
    </main>
  );
}

// ============================================================
// HEADER
// ============================================================
function Header({ authed }: { authed: boolean }) {
  return (
    <header className="relative z-40">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 pt-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-cream-50 px-3 py-1.5 rounded-sm border border-navy-200/40">
            <Image src="/logo.jpg" alt="Dennis & Associates" width={150} height={50} priority />
          </div>
        </div>
        <nav className="hidden lg:flex items-center gap-8 text-sm">
          <a href="#features" className="text-navy-600 hover:text-navy-900 transition">Features</a>
          <a href="#compliance" className="text-navy-600 hover:text-navy-900 transition">Compliance</a>
          <a href="#intelligence" className="text-navy-600 hover:text-navy-900 transition">AI Intelligence</a>
          <a href="#industries" className="text-navy-600 hover:text-navy-900 transition">Industries</a>
          <a href="#pricing" className="text-navy-600 hover:text-navy-900 transition">Pricing</a>
          <a href="#security" className="text-navy-600 hover:text-navy-900 transition">Security</a>
        </nav>
        <div className="flex items-center gap-3">
          {authed ? (
            <Link href="/dashboard" className="btn-primary">
              Open dashboard <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <>
              <Link href="/login" className="btn-ghost text-sm hidden sm:inline-flex">Sign in</Link>
              <Link href="/login" className="btn-primary">
                Request access <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

// ============================================================
// HERO
// ============================================================
function Hero() {
  const tiltRef = useRef<HTMLDivElement>(null);

  function handleMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!tiltRef.current) return;
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width - 0.5) * 10;   // ±5px
    const y = ((e.clientY - r.top) / r.height - 0.5) * 10;
    tiltRef.current.style.transform = `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
  }

  function handleLeave() {
    if (tiltRef.current) tiltRef.current.style.transform = '';
  }

  return (
    <section className="relative pt-12 lg:pt-20 pb-12 lg:pb-16">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-10 lg:gap-12 items-center">
        {/* Hero copy */}
        <div className="fade-up">
          <div className="flex items-center gap-2 mb-6">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-cream-100 border border-navy-200/40 rounded-full">
              <Radar className="w-3.5 h-3.5 text-accent" />
              <span className="text-[11px] uppercase tracking-wider2 text-navy-700">
                Compliance Radar · v0.9 beta
              </span>
            </div>
          </div>

          <h1 className="display text-[clamp(2.5rem,5.8vw,4.8rem)] text-navy-900 leading-[1.02]">
            The signal beneath
            <br />
            <span className="text-accent italic">the noise.</span>
          </h1>

          <p className="mt-6 text-base lg:text-lg text-navy-600 leading-relaxed max-w-xl">
            An AI-powered compliance intelligence platform for UK accountants.
            Live Companies House monitoring, AI lead scoring, predictive risk modelling,
            and CRM workflow automation — all in one real-time intelligence dashboard.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link href="/login" className="btn-primary text-base px-5 py-2.5">
              Open the dashboard <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="#features" className="btn-ghost text-base">
              See how it works
            </a>
          </div>

          <div className="mt-10 flex items-center gap-6 text-xs text-navy-500">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-risk-low" />
              Companies House Official Partner API
            </span>
            <span className="hidden sm:flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-risk-low" />
              UK GDPR compliant
            </span>
          </div>
        </div>

        {/* Hero dashboard mockup — wrapped in mouse-parallax tilt */}
        <div
          className="relative"
          onMouseMove={handleMove}
          onMouseLeave={handleLeave}
        >
          <div ref={tiltRef} className="parallax-tilt">
            <HeroDashboard />
          </div>
        </div>
      </div>
    </section>
  );
}

// ============================================================
// ANIMATED STATS
// ============================================================
function AnimatedStats() {
  const ref = useReveal<HTMLDivElement>(0.3);
  const [run, setRun] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setRun(true); }),
      { threshold: 0.3 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);

  return (
    <section className="bg-navy-900 text-cream-50 relative overflow-hidden">
      {/* Decorative grid */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            'linear-gradient(to right, #f7f3e9 1px, transparent 1px), linear-gradient(to bottom, #f7f3e9 1px, transparent 1px)',
          backgroundSize: '80px 80px',
        }}
      />
      <div ref={ref} className="reveal relative max-w-[1280px] mx-auto px-6 lg:px-10 py-14 lg:py-20 grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-4">
        <CounterStat run={run} target={2_400_000} suffix="" prefix="" format="m" label="UK Companies monitored" />
        <CounterStat run={run} target={14_200} format="comma" label="Filing deadlines tracked" />
        <CounterStat run={run} target={1_280} format="comma" label="Overdue alerts this week" />
        <CounterStat run={run} target={96} suffix="%" label="AI classification accuracy" />
      </div>
    </section>
  );
}

function CounterStat({
  run,
  target,
  label,
  suffix = '',
  prefix = '',
  format = 'comma',
}: {
  run: boolean;
  target: number;
  label: string;
  suffix?: string;
  prefix?: string;
  format?: 'comma' | 'm';
}) {
  const value = useCountUp(target, 1800, run);
  let displayed: string;
  if (format === 'm') {
    displayed = (value / 1_000_000).toFixed(1) + 'M';
  } else {
    displayed = Math.floor(value).toLocaleString('en-GB');
  }
  return (
    <div className="text-center lg:text-left">
      <div className="display text-4xl lg:text-6xl text-cream-50 tabular-nums leading-none">
        {prefix}{displayed}{suffix}
      </div>
      <div className="mt-3 text-[11px] uppercase tracking-wider2 text-cream-200/60">
        {label}
      </div>
    </div>
  );
}

// ============================================================
// TRUST STRIP
// ============================================================
function TrustStrip() {
  return (
    <section className="bg-cream-100 border-y border-navy-200/30">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-8">
        <div className="text-center text-[11px] uppercase tracking-wider2 text-navy-500 mb-5">
          Powered by official UK data sources
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-xs lg:text-sm text-navy-600 font-medium">
          <TrustChip>Companies House</TrustChip>
          <TrustChip>HMRC Open Data</TrustChip>
          <TrustChip>ICO Registered</TrustChip>
          <TrustChip>OpenAI</TrustChip>
          <TrustChip>HubSpot · Pipedrive</TrustChip>
          <TrustChip>Slack · Resend</TrustChip>
        </div>
      </div>
    </section>
  );
}

function TrustChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-2">
      <span className="w-1 h-1 rounded-full bg-accent" />
      {children}
    </span>
  );
}

// ============================================================
// DASHBOARD SHOWCASE
// ============================================================
function DashboardShowcaseSection() {
  const ref = useReveal<HTMLDivElement>(0.1);
  return (
    <section id="features" className="py-20 lg:py-28">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-12">
          <div className="eyebrow mb-3">Inside the platform</div>
          <h2 className="display text-3xl lg:text-5xl text-navy-900 max-w-3xl mx-auto">
            One pane of glass for every UK compliance signal.
          </h2>
          <p className="mt-5 text-navy-600 max-w-2xl mx-auto leading-relaxed">
            Companies House filings, risk scoring, AI classification, and CRM workflows —
            unified in a single real-time intelligence dashboard your team will actually want to open.
          </p>
        </div>

        <div ref={ref} className="reveal">
          <DashboardShowcase />
        </div>
      </div>
    </section>
  );
}

// ============================================================
// INTELLIGENCE FEATURES
// ============================================================
function IntelligenceFeatures() {
  return (
    <section id="intelligence" className="bg-navy-900 text-cream-50 py-20 lg:py-28">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-14">
          <div className="text-[11px] uppercase tracking-wider2 text-accent mb-3">Intelligence layer</div>
          <h2 className="display text-3xl lg:text-5xl text-cream-50 max-w-3xl mx-auto">
            Three engines. One stream of qualified leads.
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <FeatureCard
            icon={Building2}
            number="01"
            title="Companies House intelligence"
            body="Live filing-stream ingestion. Overdue accounts, confirmation-statement gaps, strike-off warnings, dormant-to-active flips — surfaced within minutes, not quarters."
          />
          <FeatureCard
            icon={Cpu}
            number="02"
            title="AI lead scoring"
            body="A rule-based scoring engine (35-point overdue, 15-point priority sector, 10-point hiring signal…) combined with an OpenAI classifier that writes the outreach summary for you."
          />
          <FeatureCard
            icon={Sparkles}
            number="03"
            title="Predictive risk modelling"
            body="Tiered compliance risk with strike-off window prediction, officer-churn detection, and dissolved/liquidation state tracking. The clock starts running before they know it."
          />
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  icon: Icon,
  number,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  number: string;
  title: string;
  body: string;
}) {
  return (
    <div className="lift bg-navy-800/40 border border-navy-700/50 rounded-sm p-7 backdrop-blur-sm">
      <div className="flex items-start justify-between mb-5">
        <div className="w-11 h-11 rounded-sm bg-accent/15 border border-accent/30 flex items-center justify-center">
          <Icon className="w-5 h-5 text-accent" />
        </div>
        <span className="font-mono text-[11px] text-accent/60">{number}</span>
      </div>
      <h3 className="display text-2xl text-cream-50 mb-3">{title}</h3>
      <p className="text-cream-100/70 leading-relaxed text-sm">{body}</p>
    </div>
  );
}

// ============================================================
// TARGET INDUSTRIES
// ============================================================
function TargetIndustries() {
  return (
    <section id="industries" className="py-20 lg:py-28 paper-bg">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-14">
          <div className="eyebrow mb-3">Built for the niches you already win</div>
          <h2 className="display text-3xl lg:text-5xl text-navy-900 max-w-3xl mx-auto">
            Priority sectors with dedicated scoring logic.
          </h2>
          <p className="mt-4 text-navy-600 max-w-2xl mx-auto leading-relaxed">
            Sector weights and signal sources are tuned per industry — what counts as
            urgency in construction is not what counts in eCommerce.
          </p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <IndustryCard icon={HardHat} title="Construction & CIS"
            blurb="CIS subcontractor identification, monthly return tracking, late-payment flags."
            stat="SIC 41–43" />
          <IndustryCard icon={Home} title="Landlords & property"
            blurb="Letting agencies, holding companies, MTD for landlords, ATED radar."
            stat="SIC 68" />
          <IndustryCard icon={ShoppingBag} title="eCommerce"
            blurb="Online sellers, marketplace VAT, OSS/IOSS readiness, Shopify signals."
            stat="SIC 47.91" />
          <IndustryCard icon={Heart} title="Care providers"
            blurb="Residential, domiciliary, healthcare staffing. CQC + filing combined."
            stat="SIC 86–88" />
          <IndustryCard icon={Briefcase} title="Consultants"
            blurb="Professional services, IR35 exposure, off-payroll engagement risk."
            stat="SIC 70.22" />
          <IndustryCard icon={Rocket} title="Newly incorporated"
            blurb="First-year filing prompts, founder outreach, growth-stage capture."
            stat="< 12 months old" />
        </div>
      </div>
    </section>
  );
}

function IndustryCard({
  icon: Icon,
  title,
  blurb,
  stat,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  blurb: string;
  stat: string;
}) {
  return (
    <div className="lift bg-white border border-navy-200/50 rounded-sm p-6 group">
      <div className="flex items-center justify-between mb-4">
        <div className="w-10 h-10 rounded-sm bg-cream-100 border border-navy-200/40 flex items-center justify-center group-hover:bg-accent/10 group-hover:border-accent/30 transition-colors">
          <Icon className="w-5 h-5 text-navy-700 group-hover:text-accent transition-colors" />
        </div>
        <span className="font-mono text-[10px] text-navy-400">{stat}</span>
      </div>
      <h3 className="display text-xl text-navy-900 mb-2">{title}</h3>
      <p className="text-sm text-navy-600 leading-relaxed">{blurb}</p>
    </div>
  );
}

// ============================================================
// PRODUCT SCREENSHOTS (lead card / alert / table)
// ============================================================
function ProductScreenshots() {
  return (
    <section id="compliance" className="bg-cream-100 py-20 lg:py-28">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-14">
          <div className="eyebrow mb-3">Anatomy of a qualified lead</div>
          <h2 className="display text-3xl lg:text-5xl text-navy-900 max-w-3xl mx-auto">
            From filing event to outreach in under a minute.
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <LeadCardMockup />
          <AlertMockup />
          <TableMockup />
        </div>
      </div>
    </section>
  );
}

function LeadCardMockup() {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm p-5 lift">
      <div className="eyebrow mb-3">Step 1 · A lead is born</div>
      <div className="flex items-center gap-2 mb-2">
        <span className="pill bg-risk-critical/15 text-risk-critical capitalize glow-pulse">urgent</span>
        <span className="text-[10px] uppercase tracking-wider2 text-accent">CIS / Construction</span>
      </div>
      <div className="display text-lg text-navy-900">Thornbury Construction Ltd</div>
      <div className="font-mono text-[10px] text-navy-500 mt-1">
        CRN 09182734 · Vauxhall, SW9 · SIC 43.21
      </div>
      <p className="mt-3 text-xs text-navy-700 leading-relaxed">
        Construction company in Vauxhall with overdue accounts (14 days). CIS-registered.
        High likelihood of urgent compliance support need.
      </p>
      <div className="mt-4 pt-4 border-t border-navy-200/40 flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-wider2 text-navy-500">Est. annual value</div>
          <div className="display text-xl text-accent">£4,800<span className="text-[10px] text-navy-500 font-sans">/yr</span></div>
        </div>
        <div className="text-right">
          <div className="font-mono tabular-nums text-navy-900">87</div>
          <div className="text-[9px] uppercase tracking-wider2 text-navy-500">score</div>
        </div>
      </div>
    </div>
  );
}

function AlertMockup() {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm overflow-hidden lift">
      <div className="px-5 pt-5">
        <div className="eyebrow mb-3">Step 2 · Alert dispatched</div>
      </div>
      {/* Slack-style message */}
      <div className="mx-5 mb-3 border border-navy-200/40 rounded-sm overflow-hidden">
        <div className="bg-navy-900 px-3 py-2 flex items-center gap-2">
          <div className="w-5 h-5 rounded-sm bg-accent/20 flex items-center justify-center">
            <Bell className="w-3 h-3 text-accent" />
          </div>
          <span className="text-[11px] text-cream-50 font-medium">#compliance-radar</span>
          <span className="text-[10px] text-cream-200/50 ml-auto">now</span>
        </div>
        <div className="p-3 bg-cream-50">
          <div className="text-[11px] font-semibold text-navy-900 mb-1">
            🚨 High-value lead · Score 87
          </div>
          <div className="text-[11px] text-navy-700">
            <span className="font-medium">Thornbury Construction Ltd</span> · Overdue accounts (14d)
          </div>
          <div className="text-[10px] text-navy-500 mt-1.5 font-mono">
            CRN 09182734 · ~£4.8k ARR
          </div>
        </div>
      </div>
      {/* Email + Telegram status */}
      <div className="px-5 pb-5 space-y-1.5">
        <div className="flex items-center gap-2 text-[11px] text-navy-600">
          <CheckCircle2 className="w-3 h-3 text-risk-low" />
          Email · Resend · delivered 4s
        </div>
        <div className="flex items-center gap-2 text-[11px] text-navy-600">
          <CheckCircle2 className="w-3 h-3 text-risk-low" />
          Telegram · @da-radar-bot · delivered 6s
        </div>
        <div className="flex items-center gap-2 text-[11px] text-navy-600">
          <CheckCircle2 className="w-3 h-3 text-risk-low" />
          HubSpot deal created · pipeline: Urgent
        </div>
      </div>
    </div>
  );
}

function TableMockup() {
  return (
    <div className="bg-white border border-navy-200/50 rounded-sm overflow-hidden lift">
      <div className="px-5 pt-5">
        <div className="eyebrow mb-3">Step 3 · Tracked in pipeline</div>
      </div>
      <div className="divide-y divide-navy-200/40">
        <PipelineRow stage="Qualified" name="Camden Property" value="£3,200" days="4d" />
        <PipelineRow stage="Contacted" name="Thornbury Co." value="£4,800" days="2d" highlight />
        <PipelineRow stage="In progress" name="Highbury Care" value="£5,400" days="6d" />
        <PipelineRow stage="Won" name="Pixel & Pine" value="£2,100" days="—" won />
      </div>
      <div className="px-5 py-3 bg-cream-50 border-t border-navy-200/40 text-[11px] text-navy-600 flex justify-between">
        <span>4 active deals</span>
        <span className="font-mono text-navy-900">£15.5k pipeline</span>
      </div>
    </div>
  );
}

function PipelineRow({
  stage,
  name,
  value,
  days,
  highlight,
  won,
}: {
  stage: string;
  name: string;
  value: string;
  days: string;
  highlight?: boolean;
  won?: boolean;
}) {
  return (
    <div className={`px-5 py-3 grid grid-cols-[auto_1fr_auto] items-center gap-3 ${highlight ? 'bg-accent/5' : ''}`}>
      <span className={`text-[9px] uppercase tracking-wider2 px-1.5 py-0.5 rounded-sm ${
        won ? 'bg-risk-low/15 text-risk-low' :
        highlight ? 'bg-accent/15 text-accent' : 'bg-navy-100 text-navy-600'
      }`}>{stage}</span>
      <div className="text-xs font-medium text-navy-900 truncate">{name}</div>
      <div className="text-right">
        <div className="text-xs font-medium text-navy-900 tabular-nums">{value}</div>
        <div className="text-[10px] text-navy-500">{days}</div>
      </div>
    </div>
  );
}

// ============================================================
// SECURITY / TRUST SECTION
// ============================================================
function SecuritySection() {
  return (
    <section id="security" className="py-20 lg:py-28">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-12 items-start">
          <div className="lg:sticky lg:top-10">
            <div className="eyebrow mb-3">Security & trust</div>
            <h2 className="display text-3xl lg:text-5xl text-navy-900">
              Built for accountancy.
              <br />
              <span className="text-accent italic">Audited like it.</span>
            </h2>
            <p className="mt-5 text-navy-600 leading-relaxed">
              Your clients trust you with their numbers. We carry the same standard
              for every byte we process. UK GDPR by default, audit trails by design,
              role-based access from day one.
            </p>
            <div className="mt-6">
              <ComplianceSeal />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <SecurityCard icon={Shield} title="UK GDPR compliant"
              body="Lawful-basis tracking, automated DSAR workflows, retention policies on every table." />
            <SecurityCard icon={Database} title="Companies House Official API"
              body="Direct partner integration. Real-time streaming. Zero third-party intermediaries." />
            <SecurityCard icon={Lock} title="Encrypted infrastructure"
              body="TLS 1.3 in flight, AES-256 at rest. Secrets in environment vaults, never source." />
            <SecurityCard icon={ScrollText} title="Append-only audit logging"
              body="Every login, lead change, suppression and CRM push captured with IP + actor." />
            <SecurityCard icon={KeyRound} title="Role-based access control"
              body="Admin / Manager / Viewer separation. JWT with refresh tokens + lockout." />
            <SecurityCard icon={Cloud} title="Secure cloud hosting"
              body="UK / EU regions only. Docker-native. SOC 2 ready architecture." />
          </div>
        </div>
      </div>
    </section>
  );
}

function SecurityCard({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
}) {
  return (
    <div className="lift bg-white border border-navy-200/50 rounded-sm p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-sm bg-cream-100 border border-navy-200/40 flex items-center justify-center">
          <Icon className="w-4 h-4 text-navy-700" />
        </div>
        <h3 className="display text-base text-navy-900">{title}</h3>
      </div>
      <p className="text-xs text-navy-600 leading-relaxed">{body}</p>
    </div>
  );
}

function ComplianceSeal() {
  return (
    <div className="inline-flex items-center gap-4 bg-cream-100 border border-navy-200/40 rounded-sm p-4">
      <div className="w-14 h-14 relative">
        <svg viewBox="0 0 56 56" className="w-14 h-14">
          <circle cx="28" cy="28" r="26" fill="none" stroke="#c89b3c" strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="28" cy="28" r="22" fill="#f7f3e9" stroke="#142648" strokeWidth="1.5" />
          <BadgeCheck className="text-accent" />
          <path d="M22 28 L26 32 L34 22" stroke="#c89b3c" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider2 text-navy-500">Verified</div>
        <div className="display text-sm text-navy-900">ICO Registered · UK GDPR</div>
        <div className="text-[10px] text-navy-500 mt-0.5 font-mono">Ref. ZB6xxxxx</div>
      </div>
    </div>
  );
}

// ============================================================
// PRICING
// ============================================================
function Pricing() {
  return (
    <section id="pricing" className="bg-cream-100 py-20 lg:py-28">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-14">
          <div className="eyebrow mb-3">Pricing</div>
          <h2 className="display text-3xl lg:text-5xl text-navy-900 max-w-3xl mx-auto">
            Internal tool. Managed service. White-labelled SaaS.
          </h2>
          <p className="mt-4 text-navy-600 max-w-2xl mx-auto">
            Run it yourself, have us run it, or resell it to your peer firms.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <PriceCard
            tier="Internal"
            price="£0"
            period="self-hosted"
            blurb="The codebase, running on your infrastructure. For D&A's own use."
            features={[
              'Full source — Docker Compose',
              'Companies House polling + stream',
              'Slack / Telegram / Email alerts',
              'HubSpot / Pipedrive CRM sync',
              'Up to 5 internal users',
            ]}
            cta="Open dashboard"
          />
          <PriceCard
            tier="Managed"
            price="£480"
            period="/month"
            blurb="We host it, monitor it, and tune the scoring for your client base."
            features={[
              'Everything in Internal',
              'Hosted on UK infrastructure',
              'Sentry monitoring + uptime SLA',
              'Quarterly scoring-model tuning',
              'Unlimited users · priority support',
            ]}
            cta="Talk to us"
            featured
          />
          <PriceCard
            tier="Whitelabel"
            price="Custom"
            period="annual"
            blurb="Your brand, your domain, sold to peer firms. We power the back end."
            features={[
              'Everything in Managed',
              'Custom domain + branding',
              'Multi-tenant data isolation',
              'Reseller dashboard',
              'Revenue share or licence',
            ]}
            cta="Speak with founders"
          />
        </div>
      </div>
    </section>
  );
}

function PriceCard({
  tier,
  price,
  period,
  blurb,
  features,
  cta,
  featured,
}: {
  tier: string;
  price: string;
  period: string;
  blurb: string;
  features: string[];
  cta: string;
  featured?: boolean;
}) {
  return (
    <div className={`lift rounded-sm border p-7 flex flex-col relative ${
      featured
        ? 'bg-navy-900 text-cream-50 border-navy-800 lg:scale-[1.02]'
        : 'bg-white text-navy-900 border-navy-200/50'
    }`}>
      {featured && (
        <div className="absolute -top-3 left-7 px-2.5 py-1 bg-accent text-cream-50 text-[10px] uppercase tracking-wider2 rounded-sm">
          Recommended
        </div>
      )}
      <div className="eyebrow mb-3">{tier}</div>
      <div className="display text-5xl">
        {price}
        <span className="text-sm font-sans text-current opacity-60 ml-1">{period}</span>
      </div>
      <p className={`mt-3 text-sm leading-relaxed ${featured ? 'text-cream-200/70' : 'text-navy-600'}`}>
        {blurb}
      </p>

      <ul className="my-6 space-y-2.5 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-sm">
            <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${featured ? 'text-accent' : 'text-risk-low'}`} />
            <span className={featured ? 'text-cream-100' : 'text-navy-700'}>{f}</span>
          </li>
        ))}
      </ul>

      <Link
        href="/login"
        className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-sm transition ${
          featured
            ? 'bg-accent text-cream-50 hover:bg-accent/90'
            : 'bg-navy-700 text-cream-50 hover:bg-navy-800'
        }`}
      >
        {cta} <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}

// ============================================================
// FOOTER CTA + FOOTER
// ============================================================
function FooterCTA({ authed }: { authed: boolean }) {
  return (
    <section className="bg-navy-900 text-cream-50 py-20 lg:py-28 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            'linear-gradient(to right, #f7f3e9 1px, transparent 1px), linear-gradient(to bottom, #f7f3e9 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />
      <div className="relative max-w-[1280px] mx-auto px-6 lg:px-10 text-center">
        <Radar className="w-8 h-8 text-accent mx-auto mb-6" />
        <h2 className="display text-3xl lg:text-5xl text-cream-50 max-w-3xl mx-auto leading-[1.05]">
          The next overdue filing
          <br />
          <span className="text-accent italic">is your next client.</span>
        </h2>
        <p className="mt-5 text-cream-200/70 max-w-xl mx-auto leading-relaxed">
          Stop reacting to year-end. Start every conversation already knowing the answer.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
          <Link href={authed ? '/dashboard' : '/login'} className="btn-primary bg-accent hover:bg-accent/90 text-base px-5 py-2.5">
            {authed ? 'Open the dashboard' : 'Request access'}
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a href="#features" className="text-cream-100/70 text-sm hover:text-cream-50 transition">
            See features →
          </a>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-navy-900 text-cream-200/50 py-10 border-t border-navy-800">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 flex flex-col lg:flex-row items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-3">
          <div className="bg-cream-50 px-2 py-1 rounded-sm">
            <Image src="/logo.jpg" alt="Dennis & Associates" width={110} height={36} />
          </div>
          <span className="hidden sm:inline">· Compliance Radar v0.9</span>
        </div>
        <div className="flex items-center gap-6">
          <span>© 2026 Dennis & Associates Accountants</span>
          <a href="#" className="hover:text-cream-100">Privacy</a>
          <a href="#" className="hover:text-cream-100">Terms</a>
        </div>
      </div>
    </footer>
  );
}
