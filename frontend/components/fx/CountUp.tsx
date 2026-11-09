"use client";

import { useEffect, useState } from "react";
import { prefersReducedMotion, useInView } from "./motion";

/** Counts from 0 to `to` the first time it is seen. Shows the final number straight away for reduced motion. */
export default function CountUp({ to, ms = 1100 }: { to: number; ms?: number }) {
  const [ref, seen] = useInView<HTMLSpanElement>();
  const [n, setN] = useState(to);
  useEffect(() => {
    if (!seen || prefersReducedMotion() || to === 0) return;
    let raf = 0;
    const t0 = performance.now();
    setN(0);
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      setN(Math.round(to * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, to, ms]);
  return <span ref={ref}>{n}</span>;
}
