"use client";

import { useTranslations } from "next-intl";
import type { Tracker } from "@/lib/types";

export default function ProgressTracker({ tracker }: { tracker: Tracker }) {
  const t = useTranslations("tracker");
  return (
    <nav aria-label={t("label")} className="mb-6">
      <ol className="flex flex-wrap gap-2">
        {tracker.steps.map((s, i) => (
          <li
            key={s.id}
            aria-current={s.active ? "step" : undefined}
            className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${
              s.active
                ? "border-brand-700 bg-brand-700 text-white"
                : s.done
                  ? "border-green-700 bg-green-50 text-green-900"
                  : "border-slate-400 bg-white text-slate-800"
            }`}
          >
            <span aria-hidden="true">{s.done ? "✓" : i + 1}</span>
            <span>{t(s.id)}</span>
            <span className="sr-only">{s.active ? t("current") : s.done ? t("done") : ""}</span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
