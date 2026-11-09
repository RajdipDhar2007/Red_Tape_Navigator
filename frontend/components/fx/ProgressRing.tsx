"use client";

/** A circular progress indicator (0..100) with an animated stroke. The value is also exposed as text for screen readers. */
export default function ProgressRing({ percent, size = 64, label }: { percent: number; size?: number; label: string }) {
  const r = (size - 10) / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(100, percent));
  return (
    <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(p)} aria-label={label} className="relative inline-flex shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth="7" className="stroke-slate-200" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth="7" strokeLinecap="round" className={p >= 100 ? "stroke-indgreen-600" : "stroke-saffron-500"} strokeDasharray={c} strokeDashoffset={c * (1 - p / 100)} style={{ transition: "stroke-dashoffset .7s cubic-bezier(.2,.7,.2,1)" }} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-head text-sm font-bold text-navy-900">{Math.round(p)}%</span>
    </div>
  );
}
