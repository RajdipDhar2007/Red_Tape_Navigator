import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

type Item = { h: string; p: string };

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "help" });
  return { title: t("title"), description: t("intro") };
}

/** Plain questions and answers. The text lives in the message files so it exists in every interface language. */
export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("help");
  const tl = await getTranslations("legal");
  const items = Object.entries(t.raw("items") as Record<string, Item>).map(([id, v]) => ({ id, h: v.h, p: v.p.split("\n") }));
  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p>{t("intro")}</p>
      {items.map((q) => (
        <section key={q.id} aria-labelledby={`help-${q.id}`} className="card space-y-2">
          <h2 id={`help-${q.id}`} className="text-lg font-semibold">
            {q.h}
          </h2>
          {q.p.length === 1 ? (
            <p>{q.p[0]}</p>
          ) : (
            <ul className="list-disc space-y-1 pl-5">
              {q.p.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </section>
      ))}
      <p>
        <Link className="underline" href={`/${locale}/privacy`}>
          {tl("linkPrivacy")}
        </Link>
      </p>
    </article>
  );
}
