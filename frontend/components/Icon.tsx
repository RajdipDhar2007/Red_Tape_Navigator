type Name = "goal" | "search" | "chat" | "shield" | "check" | "lock" | "globe" | "file" | "arrow" | "copy" | "external" | "store" | "food" | "scissors" | "factory" | "dumbbell" | "laptop" | "plant" | "home" | "user" | "alert";

const PATHS: Record<Name, string> = {
  goal: "M12 2a10 10 0 100 20 10 10 0 000-20zm0 5a5 5 0 110 10 5 5 0 010-10zm0 3a2 2 0 100 4 2 2 0 000-4z",
  search: "M10.5 3a7.5 7.5 0 015.9 12.1l4.3 4.3-1.4 1.4-4.3-4.3A7.5 7.5 0 1110.5 3zm0 2a5.5 5.5 0 100 11 5.5 5.5 0 000-11z",
  chat: "M4 4h16a2 2 0 012 2v10a2 2 0 01-2 2H9l-5 4v-4a2 2 0 01-2-2V6a2 2 0 012-2zm3 5v2h10V9H7zm0 4v2h7v-2H7z",
  shield: "M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5l8-3zm-1 13l6-6-1.4-1.4L11 12.2 8.4 9.6 7 11l4 4z",
  check: "M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z",
  lock: "M17 9V7a5 5 0 00-10 0v2H5v12h14V9h-2zm-8-2a3 3 0 016 0v2H9V7zm3 6a2 2 0 011 3.7V19h-2v-2.3A2 2 0 0112 13z",
  globe: "M12 2a10 10 0 100 20 10 10 0 000-20zm6.9 9h-3a15 15 0 00-1.2-5.1A8 8 0 0118.9 11zM12 4c.8 1 1.7 3.2 2 7h-4c.3-3.800 1.200-6 2-7zM4.1 13h3a15 15 0 001.200 5.100A8 8 0 014.100 13zm3-2h-3a8 8 0 014.200-5.100A15 15 0 007.100 11zM12 20c-.8-1-1.700-3.200-2-7h4c-.3 3.800-1.200 6-2 7zm2.700-1.900A15 15 0 0015.900 13h3a8 8 0 01-4.200 5.100z",
  file: "M6 2h8l6 6v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4a2 2 0 012-2zm7 1.500V9h5.500L13 3.500zM8 13v2h8v-2H8zm0 4v2h5v-2H8z",
  arrow: "M13 5l7 7-7 7-1.400-1.400L16.200 13H4v-2h12.200l-4.600-4.600L13 5z",
  copy: "M8 3h10a2 2 0 012 2v12h-2V5H8V3zM5 7h10a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V9a2 2 0 012-2zm0 2v10h10V9H5z",
  external: "M14 3h7v7h-2V6.400l-8.300 8.300-1.400-1.400L17.600 5H14V3zM5 5h6v2H5v12h12v-6h2v6a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z",
  store: "M4 4h16l1 5a3 3 0 01-2 2.800V20H5v-8.200A3 3 0 013 9l1-5zm3 9v5h4v-5H7zm6 0v5h4v-5h-4z",
  food: "M7 2v8a3 3 0 002 2.800V22h2V12.800A3 3 0 0013 10V2h-2v6H9.500V2h-2v6H7V2zm10 0c-2.200 1.200-3 3.700-3 6.500 0 2 .800 3.500 2 4V22h2V2h-1z",
  scissors: "M9.600 7.200a3.500 3.500 0 10-2.100 2.600L10 12l-2.500 2.200a3.500 3.500 0 102.100 2.600L21 7V5L9.600 7.200zM6 8a1.500 1.500 0 110-3 1.500 1.500 0 010 3zm0 11a1.500 1.500 0 110-3 1.500 1.500 0 010 3zm6-6.500a.5.5 0 110-1 .5.5 0 010 1zM13.500 13.500L21 19v-2l-5.500-4z",
  factory: "M2 21V9l6 3V9l6 3V5h4l1 7h3v9H2zm4-6v3h2v-3H6zm5 0v3h2v-3h-2zm5 0v3h2v-3h-2z",
  dumbbell: "M3 9h2V7h2v10H5v-2H3V9zm18 0h-2V7h-2v10h2v-2h2V9zM9 11h6v2H9v-2z",
  laptop: "M4 5h16a1 1 0 011 1v10h1v2H2v-2h1V6a1 1 0 011-1zm1 2v9h14V7H5z",
  plant: "M12 22v-9m0 0C12 8 15 5 20 4c0 5-3 8-8 9zm0 0C12 9.500 9.500 7 4 6.500c.5 4.500 3 6.500 8 6.500z",
  home: "M12 3l10 9h-3v9h-5v-6h-4v6H5v-9H2l10-9z",
  user: "M12 12a5 5 0 100-10 5 5 0 000 10zm0 2c-4.400 0-8 2.200-8 5v3h16v-3c0-2.800-3.600-5-8-5z",
  alert: "M12 2l11 20H1L12 2zm-1 7v6h2V9h-2zm0 8v2h2v-2h-2z",
};

export default function Icon({ name, size = 22, className = "" }: { name: Name; size?: number; className?: string }) {
  const stroked = name === "plant";
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} aria-hidden="true" focusable="false"
      fill={stroked ? "none" : "currentColor"} stroke={stroked ? "currentColor" : "none"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[name]} />
    </svg>
  );
}
export type IconName = Name;
