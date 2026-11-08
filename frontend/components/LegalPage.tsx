import { getTranslations } from "next-intl/server";
import PolicyFacts from "./PolicyFacts";

type Section = { h: string; p: string };

/** Privacy policy / terms. Text lives in the message files (en/hi/bn); retention, region and grievance contact are live. */
export default async function LegalPage({ kind }: { kind: "privacy" | "terms" }) {
  const t = await getTranslations("legal");
  const sections = Object.values(t.raw(kind) as Record<string, Section>).map((s) => ({ h: s.h, p: s.p.split("\n") }));
  const reviewed = process.env.NEXT_PUBLIC_LEGAL_REVIEWED === "true";
  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">{t(kind === "privacy" ? "privacyTitle" : "termsTitle")}</h1>
      {!reviewed && (
        <p role="note" className="rounded border border-amber-500 bg-amber-50 p-3 text-sm text-amber-950">
          {t("draft")}
        </p>
      )}
      {kind === "privacy" && <PolicyFacts />}
      {sections.map((s) => (
        <section key={s.h} className="space-y-2">
          <h2 className="text-lg font-semibold">{s.h}</h2>
          {s.p.length === 1 ? (
            <p>{s.p[0]}</p>
          ) : (
            <ul className="list-disc space-y-1 pl-5">
              {s.p.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </article>
  );
}
