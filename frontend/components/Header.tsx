"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { api, clearTokens, hasToken } from "@/lib/api";
import LogoMark from "./LogoMark";

const NAMES: Record<string, string> = { en: "English", bn: "বাংলা", hi: "हिन्दी" };
type Me = { email: string; role: string };

export default function Header() {
  const t = useTranslations("app");
  const tn = useTranslations("nav");
  const ts = useTranslations("staff");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (!hasToken()) {
      setMe(null);
      return;
    }
    api<Me>("/auth/me")
      .then(setMe)
      .catch(() => setMe(null));
  }, [pathname]);

  const link = (href: string, label: string) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        aria-current={active ? "page" : undefined}
        className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${active ? "bg-navy-700 text-white" : "text-navy-800 hover:bg-navy-50"}`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="tricolour-bar h-1" aria-hidden="true" />
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
        <Link href="/" className="flex items-center gap-3" aria-label={t("title")}>
          <LogoMark size={42} />
          <span className="leading-tight">
            <span className="block font-head text-lg font-bold text-navy-900">{t("title")}</span>
            <span className="hidden text-xs font-medium text-slate-600 sm:block">{t("subtitle")}</span>
          </span>
        </Link>

        <nav aria-label={tn("label")} className="flex flex-wrap items-center gap-1.5">
          {me && link("/", tn("applications"))}
          {me && me.role !== "citizen" && link("/staff", ts("link"))}
          {me && link("/account", tn("account"))}
          <label className="ml-1 flex items-center gap-1.5 text-sm">
            <span className="sr-only">{t("language")}</span>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" className="text-navy-700" fill="currentColor">
              <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm6.900 9h-3a15 15 0 00-1.200-5.100A8 8 0 0118.900 11zM12 4c.8 1 1.700 3.200 2 7h-4c.3-3.800 1.200-6 2-7zM4.100 13h3a15 15 0 001.200 5.100A8 8 0 014.100 13zm3-2h-3a8 8 0 014.200-5.100A15 15 0 007.100 11zM12 20c-.8-1-1.700-3.200-2-7h4c-.3 3.800-1.200 6-2 7zm2.700-1.900A15 15 0 0015.900 13h3a8 8 0 01-4.200 5.100z" />
            </svg>
            <select
              className="rounded-lg border border-navy-200 bg-white px-2 py-1.5 text-sm font-medium text-navy-800"
              value={locale}
              onChange={(e) => router.replace(pathname, { locale: e.target.value })}
            >
              {routing.locales.map((l) => (
                <option key={l} value={l} lang={l}>
                  {NAMES[l]}
                </option>
              ))}
            </select>
          </label>
          {me && (
            <button
              type="button"
              className="btn-secondary !px-3 !py-1.5 text-sm"
              onClick={() => {
                clearTokens();
                setMe(null);
                router.push("/");
                router.refresh();
              }}
            >
              {t("logout")}
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
