"use client";

import { useFormatter, useTranslations } from "next-intl";

type Props = { source_url: string; fetched_at: string; content_hash: string; confidence: number; verify: boolean };

/** Every regulatory claim is rendered with this: source link, fetch time, content hash, confidence, verify badge. */
export default function CitationLine({ source_url, fetched_at, content_hash, confidence, verify }: Props) {
  const t = useTranslations("checklist");
  const f = useFormatter();
  let host = source_url;
  try {
    host = new URL(source_url).hostname;
  } catch {
    /* keep raw */
  }
  return (
    <p className="mt-1 text-xs text-slate-700">
      {t("source")}:{" "}
      <a className="text-brand-700 underline" href={source_url} target="_blank" rel="noopener noreferrer">
        {host}
      </a>{" "}
      · {t("fetched")} {f.dateTime(new Date(fetched_at), { dateStyle: "medium" })} · {t("confidence")} {Math.round(confidence * 100)}% ·{" "}
      <span title={content_hash}>#{content_hash.slice(0, 8)}</span>
      {verify && (
        <span className="badge ml-2 bg-amber-200 text-amber-950" title={t("verifyHelp")}>
          {t("verify")}
        </span>
      )}
    </p>
  );
}
