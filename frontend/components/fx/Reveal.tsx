"use client";

import type { ReactNode } from "react";
import { useInView } from "./motion";

/** Fades and lifts its children in when they scroll into view. `delay` (ms) staggers siblings. */
export default function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} className={`${seen ? "animate-fade-up" : "opacity-0"} ${className}`} style={seen ? { animationDelay: `${delay}ms` } : undefined}>
      {children}
    </div>
  );
}
