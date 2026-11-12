/** Decorative 24-spoke wheel used as a background accent. The app logo itself is public/logo.png. */
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
