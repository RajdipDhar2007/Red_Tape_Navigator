import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import Header from "@/components/Header";
import "../globals.css";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "app" });
  return { title: t("title"), description: t("tagline") };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "app" });
  const demo = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider>
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:p-3">
            {t("skip")}
          </a>
          <Header />
          {demo && (
            <div role="note" className="border-b border-amber-400 bg-amber-100 px-4 py-2 text-sm text-amber-950">
              {t("demoBanner")}
            </div>
          )}
          <main id="main" className="mx-auto w-full max-w-5xl px-4 py-6">
            {children}
          </main>
          <footer className="mx-auto max-w-5xl px-4 pb-10 text-sm text-slate-700">
            <p role="note">{t("disclaimer")}</p>
          </footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
