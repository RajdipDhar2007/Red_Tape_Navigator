"use client";

import { useLocale, useTranslations } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { useEffect, useState } from "react";
import { api, clearTokens, hasToken } from "@/lib/api";

const NAMES: Record<string, string> = { en: "English", bn: "বাংলা", hi: "हिन्दी" };

export default function Header() {
  const t = useTranslations("app");
  const locale = useLocale();
  const pathname = usePathname();
  const ts = useTranslations("staff");
  const router = useRouter();
  const [staff, setStaff] = useState(false);
  useEffect(() => {
    if (!hasToken()) return;
    api<{ role: string }>("/auth/me")
      .then((m) => setStaff(m.role !== "citizen"))
      .catch(() => setStaff(false));
  }, [pathname]);

  return (
    <header className="border-b border-slate-300 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-bold text-brand-900">
          {t("title")}
        </Link>
        <div className="flex items-center gap-3">
          {staff && (
            <Link href="/staff" className="text-sm underline">
              {ts("link")}
            </Link>
          )}
          <label className="flex items-center gap-2 text-sm">
            <span>{t("language")}</span>
            <select
              className="rounded border border-slate-500 bg-white px-2"
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
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={() => {
              clearTokens();
              router.push("/");
              router.refresh();
            }}
          >
            {t("logout")}
          </button>
        </div>
      </div>
    </header>
  );
}
