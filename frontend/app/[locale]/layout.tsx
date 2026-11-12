import type { Metadata } from "next";
import { DM_Sans, Noto_Sans_Bengali, Noto_Sans_Devanagari, Poppins } from "next/font/google";
import Link from "next/link";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import Header from "@/components/Header";
import "../globals.css";

// Headings: Poppins. Body: DM Sans. Devanagari / Bengali glyphs fall back to Noto Sans so Hindi and Bengali read cleanly.
const head = Poppins({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-head", display: "swap" });
const body = DM_Sans({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-deva", display: "swap" });
const beng = Noto_Sans_Bengali({ subsets: ["bengali"], variable: "--font-beng", display: "swap" });

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
  const tl = await getTranslations({ locale, namespace: "legal" });
  const tn = await getTranslations({ locale, namespace: "nav" });

  return (
    <html lang={locale} className={`${head.variable} ${body.variable} ${deva.variable} ${beng.variable}`}>
      <body className="flex min-h-screen flex-col">
        <NextIntlClientProvider>
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3 focus:shadow-lift">
            {t("skip")}
          </a>
          <Header />
          <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
            {children}
          </main>
          <footer className="mt-10 border-t border-slate-200 bg-white/80">
            <div className="tricolour-bar h-1" aria-hidden="true" />
            <div className="mx-auto max-w-6xl space-y-1 px-4 py-6 text-sm text-slate-700 sm:px-6">
              <p role="note" className="font-medium text-navy-900">
                {t("disclaimer")}
              </p>
              <p>{t("independent")}</p>
              <p className="space-x-4 pt-1">
                <Link className="underline" href={`/${locale}/privacy`}>
                  {tl("linkPrivacy")}
                </Link>
                <Link className="underline" href={`/${locale}/terms`}>
                  {tl("linkTerms")}
                </Link>
                <Link className="underline" href={`/${locale}/help`}>
                  {tn("help")}
                </Link>
              </p>
            </div>
          </footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
