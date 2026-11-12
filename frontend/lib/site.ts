/** Public origin of the website, for canonical links, the sitemap and social previews. */
export function siteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/+$/, "");
  // Vercel sets this at build time to the production domain (without the scheme).
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return `https://${vercel}`;
  return "http://localhost:3000";
}

/** Pages that are the same for every visitor. Everything else is behind sign-in and is kept out of search engines. */
export const PUBLIC_PATHS = ["", "/help", "/privacy", "/terms"] as const;
export const PRIVATE_PATHS = ["/account", "/session", "/staff", "/teams", "/documents", "/invite", "/reset", "/verify-email"] as const;
