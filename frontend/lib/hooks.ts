'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * Animate a number from 0 → target with easeOutQuart.
 * Only starts when the element scrolls into view (or runStart=true).
 */
export function useCountUp(target: number, durationMs = 1600, runStart = true) {
  const [value, setValue] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!runStart || startedRef.current) return;
    startedRef.current = true;
    const t0 = performance.now();
    let raf = 0;

    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / durationMs);
      const eased = 1 - Math.pow(1 - t, 4); // easeOutQuart
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else setValue(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs, runStart]);

  return value;
}

/**
 * Add `.is-visible` to a ref'd element when it scrolls into view.
 * Pair with `.reveal` class for fade-up entrance.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(
  threshold = 0.15,
): React.RefObject<T> {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('is-visible');
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            el.classList.add('is-visible');
            io.unobserve(el);
          }
        });
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  // The cast lets the ref attach to a JSX `ref={}` slot which expects
  // a non-nullable RefObject in React 18.3+ strict types.
  return ref as React.RefObject<T>;
}
