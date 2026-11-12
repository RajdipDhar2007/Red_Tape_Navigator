"use client";

import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import Icon from "./Icon";

type PolicyFactsData = {
  retention_days: number;
  data_region: string;
  grievance_contact: string;
};

type CategoryId = "all" | "getting_started" | "results" | "privacy" | "documents" | "troubleshooting";

type FaqItem = {
  id: string;
  category: Exclude<CategoryId, "all">;
  titleKey: string;
  bodyKey: string;
};

const FAQ_ITEMS: FaqItem[] = [
  { id: "what", category: "getting_started", titleKey: "q_what_h", bodyKey: "q_what_p" },
  { id: "start", category: "getting_started", titleKey: "q_start_h", bodyKey: "q_start_p" },
  { id: "ai", category: "results", titleKey: "q_ai_h", bodyKey: "q_ai_p" },
  { id: "submit", category: "results", titleKey: "q_submit_h", bodyKey: "q_submit_p" },
  { id: "data", category: "privacy", titleKey: "q_data_h", bodyKey: "q_data_p" },
  { id: "dpdp", category: "privacy", titleKey: "q_dpdp_h", bodyKey: "q_dpdp_p" },
  { id: "vault", category: "documents", titleKey: "q_vault_h", bodyKey: "q_vault_p" },
  { id: "trouble_auth", category: "troubleshooting", titleKey: "q_trouble_auth_h", bodyKey: "q_trouble_auth_p" },
  { id: "trouble_provider", category: "troubleshooting", titleKey: "q_trouble_provider_h", bodyKey: "q_trouble_provider_p" },
];

export default function HelpView() {
  const t = useTranslations("help");
  const tl = useTranslations("legal");
  const tn = useTranslations("nav");
  const searchId = useId();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CategoryId>("all");
  const [facts, setFacts] = useState<PolicyFactsData | null>(null);
  const [factsErr, setFactsErr] = useState(false);

  useEffect(() => {
    api<PolicyFactsData>("/privacy/policy")
      .then(setFacts)
      .catch(() => setFactsErr(true));
  }, []);

  const categories: { id: CategoryId; label: string }[] = [
    { id: "all", label: t("catAll") },
    { id: "getting_started", label: t("catGettingStarted") },
    { id: "results", label: t("catResults") },
    { id: "privacy", label: t("catPrivacy") },
    { id: "documents", label: t("catDocuments") },
    { id: "troubleshooting", label: t("catTroubleshooting") },
  ];

  const normQuery = query.trim().toLowerCase();
  const filtered = FAQ_ITEMS.filter((item) => {
    if (category !== "all" && item.category !== category) return false;
    if (!normQuery) return true;
    const h = t(item.titleKey).toLowerCase();
    const p = t(item.bodyKey).toLowerCase();
    return h.includes(normQuery) || p.includes(normQuery);
  });

  const hasConfiguredContact =
    facts &&
    facts.grievance_contact &&
    !facts.grievance_contact.toLowerCase().includes("not configured");

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <section className="card border-t-4 border-t-saffron-500" aria-labelledby="help-h">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 id="help-h" className="text-2xl font-bold sm:text-3xl">
              {t("title")}
            </h1>
            <p className="mt-1 text-slate-700">{t("intro")}</p>
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor={searchId} className="text-sm font-medium text-navy-900">
            {t("searchLabel")}
          </label>
          <div className="relative mt-1">
            <input
              id={searchId}
              type="search"
              className="input pl-10"
              placeholder={t("searchPlaceholder")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <span className="pointer-events-none absolute left-3 top-3 text-slate-500" aria-hidden="true">
              <Icon name="search" size={18} />
            </span>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label={t("searchLabel")}>
          {categories.map((c) => (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={category === c.id}
              className={category === c.id ? "btn !py-1.5 text-sm" : "btn-secondary !py-1.5 text-sm"}
              onClick={() => setCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </section>

      {filtered.length === 0 ? (
        <p role="status" className="card text-slate-700">
          {t("searchEmpty")}
        </p>
      ) : (
        <div className="space-y-4">
          {filtered.map((item) => (
            <section key={item.id} className="card space-y-2" aria-labelledby={`faq-${item.id}`}>
              <h2 id={`faq-${item.id}`} className="text-lg font-bold text-navy-900">
                {t(item.titleKey)}
              </h2>
              <p className="text-slate-800">{t(item.bodyKey)}</p>
            </section>
          ))}
        </div>
      )}

      <section className="card border-l-4 border-l-indgreen-600 space-y-2" aria-labelledby="help-contact-h">
        <h2 id="help-contact-h" className="flex items-center gap-2 text-lg font-bold text-navy-900">
          <Icon name="shield" size={20} className="text-indgreen-700" />
          {t("contactHeading")}
        </h2>
        <p className="text-sm text-slate-700">{t("contactIntro")}</p>
        {factsErr ? (
          <p role="alert" className="text-sm text-red-800">
            {tl("factLoadError")}
          </p>
        ) : !facts ? (
          <p aria-live="polite" className="text-sm text-slate-600">
            …
          </p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
            <li>{tl("factRetention", { days: facts.retention_days })}</li>
            <li>{tl("factRegion", { region: facts.data_region })}</li>
            <li>
              {hasConfiguredContact ? (
                tl("factGrievance", { contact: facts.grievance_contact })
              ) : (
                <span className="text-amber-950">{t("contactUnconfigured")}</span>
              )}
            </li>
          </ul>
        )}
      </section>

      <section className="card space-y-3" aria-labelledby="help-links-h">
        <h2 id="help-links-h" className="text-lg font-bold text-navy-900">
          {t("quickLinksHeading")}
        </h2>
        <div className="flex flex-wrap gap-2">
          <Link href="/" className="btn-secondary text-sm">
            {tn("applications")}
          </Link>
          <Link href="/documents" className="btn-secondary text-sm">
            {tn("documents")}
          </Link>
          <Link href="/account" className="btn-secondary text-sm">
            {tn("account")}
          </Link>
          <Link href="/teams" className="btn-secondary text-sm">
            {tn("teams")}
          </Link>
          <Link href="/privacy" className="btn-secondary text-sm">
            {tl("linkPrivacy")}
          </Link>
          <Link href="/terms" className="btn-secondary text-sm">
            {tl("linkTerms")}
          </Link>
        </div>
      </section>
    </div>
  );
}
