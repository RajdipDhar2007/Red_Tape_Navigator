"use client";

import { useEffect, useMemo, useState } from "react";
import { prefersReducedMotion } from "./motion";

const COLOURS = ["#f58a1f", "#ffa94d", "#138808", "#2e9e44", "#1f3f8f", "#86a3da", "#ffffff"];

/** A short burst of tricolour confetti. Decorative only (aria-hidden), removes itself, and is skipped for reduced motion. */
export default function Confetti({ burst }: { burst: number }) {
  const [on, setOn] = useState(false);
  const bits = useMemo(
    () =>
      Array.from({ length: 48 }, (_, i) => ({
        left: Math.round((i * 97 + burst * 31) % 100),
        delay: (i % 12) * 40,
        dur: 1500 + ((i * 53) % 900),
        drift: ((i * 37) % 160) - 80,
        spin: ((i * 71) % 720) - 360,
        colour: COLOURS[i % COLOURS.length],
        size: 6 + (i % 4) * 2,
      })),
    [burst],
  );
  useEffect(() => {
    if (!burst || prefersReducedMotion()) return;
    setOn(true);
    const t = setTimeout(() => setOn(false), 3000);
    return () => clearTimeout(t);
  }, [burst]);
  if (!on) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden" aria-hidden="true">
      {bits.map((b, i) => (
        <span
          key={i}
          className="confetti-bit"
          style={{ left: `${b.left}%`, width: b.size, height: b.size * 1.6, background: b.colour, animationDelay: `${b.delay}ms`, animationDuration: `${b.dur}ms`, ["--drift" as string]: `${b.drift}px`, ["--spin" as string]: `${b.spin}deg` }}
        />
      ))}
    </div>
  );
}
