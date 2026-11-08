"use client";

import { useTranslations } from "next-intl";
import type { Tracker } from "@/lib/types";
import Icon from "./Icon";

export default function ProgressTracker({ tracker }: { tracker: Tracker }) {
  const t = useTranslations("tracker");
  return (
    <nav aria-label={t("label")} className="mb-6 overflow-x-auto rounded-2xl bg-white p-4 shadow-card ring-1 ring-slate-200">
      <ol className="flex min-w-max items-center gap-2 sm:min-w-0">
        {tracker.steps.map((s, i) => (
          <li key={s.id} aria-current={s.active ? "step" : undefined} className="flex flex-1 items-center gap-2">
            <span
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-all ${
                s.active
                  ? "scale-110 bg-saffron-500 text-navy-900 shadow-md ring-4 ring-saffron-100"
                  : s.done
                    ? "bg-indgreen-600 text-white"
                    : "bg-slate-100 text-slate-600 ring-1 ring-slate-300"
              }`}
              aria-hidden="true"
            >
              {s.done ? <Icon name="check" size={18} /> : i + 1}
            </span>
            <span className={`text-sm font-semibold ${s.active ? "text-navy-900" : s.done ? "text-indgreen-800" : "text-slate-600"}`}>{t(s.id)}</span>
            <span className="sr-only">{s.active ? t("current") : s.done ? t("done") : ""}</span>
            {i < tracker.steps.length - 1 && <span className={`mx-1 hidden h-0.5 flex-1 rounded sm:block ${s.done ? "bg-indgreen-600" : "bg-slate-200"}`} aria-hidden="true" />}
          </li>
        ))}
      </ol>
    </nav>
  );
}
