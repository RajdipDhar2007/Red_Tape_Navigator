/**
 * Original tricolour mark with a 24-spoke wheel. It is NOT the State Emblem of India: that emblem is protected by
 * the State Emblem of India (Prohibition of Improper Use) Act, 2005 and may only be shown by authorised bodies.
 * A department deploying this app can supply its authorised emblem through NEXT_PUBLIC_EMBLEM_URL.
 */
export function ChakraWheel({ className = "", size = 24 }: { className?: string; size?: number }) {
  const spokes = Array.from({ length: 24 }, (_, i) => (i * 360) / 24);
  return (
    <svg viewBox="-50 -50 100 100" width={size} height={size} className={className} aria-hidden="true" fill="none" stroke="currentColor">
      <circle r="44" strokeWidth="5" />
      <circle r="8" fill="currentColor" strokeWidth="0" />
      {spokes.map((a) => (
        <line key={a} x1="0" y1="-10" x2="0" y2="-40" strokeWidth="2.2" strokeLinecap="round" transform={`rotate(${a})`} />
      ))}
    </svg>
  );
}

export default function LogoMark({ size = 44 }: { size?: number }) {
  const emblem = process.env.NEXT_PUBLIC_EMBLEM_URL;
  return (
    <span className="inline-flex items-center gap-2" aria-hidden="true">
      {emblem && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={emblem} alt="" height={size} style={{ height: size, width: "auto" }} />
      )}
      <span
        className="relative inline-flex items-center justify-center overflow-hidden rounded-xl shadow-card ring-1 ring-navy-200"
        style={{ width: size, height: size }}
      >
        <span className="absolute inset-0 flex flex-col">
          <span className="flex-1 bg-saffron-500" />
          <span className="flex-1 bg-white" />
          <span className="flex-1 bg-indgreen-600" />
        </span>
        <ChakraWheel size={size * 0.62} className="relative text-navy-700" />
      </span>
    </span>
  );
}
