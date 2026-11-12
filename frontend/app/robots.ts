import type { MetadataRoute } from "next";
import { routing } from "@/i18n/routing";
import { PRIVATE_PATHS, siteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: routing.locales.flatMap((l) => PRIVATE_PATHS.map((p) => `/${l}${p}`)) },
    sitemap: `${siteUrl()}/sitemap.xml`,
  };
}
