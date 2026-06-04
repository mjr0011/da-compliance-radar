'use client';

/**
 * Live ticker bar.
 *
 * Sits between the header and the hero, signalling "this system is
 * actively monitoring the UK right now." Two parts:
 *
 *   - Left: pulsing LIVE indicator + a stat that cycles every 3s
 *   - Right: an infinite-scroll marquee of recent Companies House
 *     filing events
 *
 * Numbers are illustrative but plausible — every value here is
 * within the order of magnitude the real system would produce
 * monitoring ~4k London companies on a paid Companies House key.
 */

import { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';

const ROTATING_STATS = [
  { label: 'Monitoring', value: '4,423 UK companies' },
  { label: 'Last hour', value: '12 companies flagged' },
  { label: 'Today', value: '247 filings processed' },
  { label: 'Accuracy', value: 'AI 96.2% · 24h rolling' },
];

const TICKER_EVENTS = [
  { time: '14:22:08', name: 'COBBLE YARD STUDIOS LTD',     event: 'Confirmation statement filed',        tone: 'normal' },
  { time: '14:21:54', name: 'PENNY LANE RETAIL LTD',       event: 'Accounts overdue 30 days',            tone: 'critical' },
  { time: '14:21:31', name: 'THORNBURY CONSTRUCTION LTD',  event: 'Director appointed',                  tone: 'normal' },
  { time: '14:20:48', name: 'HIGHBURY CARE GROUP LTD',     event: 'Registered office change',            tone: 'normal' },
  { time: '14:20:12', name: 'PIXEL & PINE STUDIOS LTD',    event: 'New incorporation',                   tone: 'accent' },
  { time: '14:19:33', name: 'CAMDEN PROPERTY HOLDINGS',    event: 'Confirmation statement due in 5 days', tone: 'warning' },
  { time: '14:19:05', name: 'BOW LANE BAKERIES LTD',       event: 'Dormant to active reactivation',      tone: 'accent' },
  { time: '14:18:21', name: 'MERCER & VALE CONSULTANTS',   event: 'Filed micro-entity accounts',         tone: 'normal' },
  { time: '14:17:44', name: 'KENNINGTON CABS LTD',         event: 'Strike-off notice issued',            tone: 'critical' },
  { time: '14:17:09', name: 'QUILL & INK STATIONERS LTD',  event: 'Charge created — Lloyds Bank',        tone: 'warning' },
  { time: '14:16:32', name: 'GREENWICH MERIDIAN HEALTH',   event: 'SIC code updated (86.10 → 86.90)',    tone: 'normal' },
  { time: '14:16:00', name: 'SHOREDITCH SPIRITS LTD',      event: 'Officer churn — 3rd director change', tone: 'warning' },
];

const TONE_STYLES: Record<string, string> = {
  critical: 'text-risk-critical',
  warning:  'text-risk-high',
  accent:   'text-accent',
  normal:   'text-cream-100/80',
};

export function TickerBar() {
  const [statIdx, setStatIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setStatIdx((i) => (i + 1) % ROTATING_STATS.length), 3200);
    return () => clearInterval(t);
  }, []);

  const stat = ROTATING_STATS[statIdx];

  return (
    <div className="bg-navy-900 border-y border-navy-800/60 text-cream-100 overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-2 flex items-center gap-6">
        {/* LIVE indicator + rotating stat */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="relative flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
            <span className="text-[10px] uppercase tracking-wider2 text-accent font-medium">live</span>
          </span>
          <div className="hidden sm:flex items-baseline gap-1.5 text-[11px]">
            <span className="uppercase tracking-wider2 text-cream-200/50 text-[10px]">
              {stat.label}
            </span>
            <span
              key={statIdx}
              className="text-cream-50 font-medium slide-in-right tabular-nums"
            >
              {stat.value}
            </span>
          </div>
        </div>

        {/* Divider */}
        <span className="hidden lg:block w-px h-4 bg-navy-700/80 shrink-0" />

        {/* Scrolling event marquee */}
        <div className="hidden lg:flex flex-1 overflow-hidden ticker-pause relative">
          {/* Fade masks on both ends */}
          <span className="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-navy-900 to-transparent z-10 pointer-events-none" />
          <span className="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-navy-900 to-transparent z-10 pointer-events-none" />

          <div className="ticker-track">
            {/* Render the list twice for seamless wrap */}
            {[...TICKER_EVENTS, ...TICKER_EVENTS].map((e, i) => (
              <span key={i} className="inline-flex items-center gap-2 text-[11px] mx-5">
                <Radio className="w-2.5 h-2.5 text-accent/60 shrink-0" />
                <span className="font-mono text-cream-200/40">{e.time}</span>
                <span className="text-cream-100 font-medium">{e.name}</span>
                <span className={`${TONE_STYLES[e.tone]}`}>·</span>
                <span className={`${TONE_STYLES[e.tone]}`}>{e.event}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Right-side: "last update" indicator */}
        <div className="hidden sm:flex items-center gap-1.5 shrink-0 text-[10px] uppercase tracking-wider2 text-cream-200/40">
          <span className="w-1 h-1 rounded-full bg-cream-100/40 animate-pulse" />
          updated 3s ago
        </div>
      </div>
    </div>
  );
}
