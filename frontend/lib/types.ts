export type Citation = {
  source_url: string;
  fetched_at: string;
  content_hash: string;
  confidence: number;
  needs_verification?: boolean;
  verify_with_authority?: boolean;
};

export type Claim = Citation & { id: string; key: string; text: string; category: string; data: Record<string, unknown> };

export type Step = {
  order: number;
  licence: string;
  name: string;
  form: string | null;
  depends_on: string[];
  conditional: boolean;
  municipal_data_missing: boolean;
  portal_login_required: boolean;
  claims: Record<string, Claim>;
};

export type Tracker = { current: string; steps: { id: string; done: boolean; active: boolean }[] };

export type Session = {
  id: string;
  goal: string;
  language: string;
  parsed: { activity: string | null; activity_label?: string | null; city: string | null; state: string | null; clarifying_question: string | null };
  plan: { steps?: Step[]; out_of_scope?: boolean; intent?: string };
  reviewed: boolean;
  tracker: Tracker;
  agent_mode?: string;
};

export type Question = { key: string; question: string; label: string; sensitive: boolean; options: string[]; group: string };

export type InterviewState = {
  questions: Question[];
  progress: { answered: number; total: number; skipped: string[]; percent: number };
  complete: boolean;
  ready_for_review: boolean;
  missing: string[];
};

export type ReportRow = {
  pdf_field: string;
  label: string;
  status: "filled" | "missing" | "doubtful" | "unmapped";
  value: string | null;
  source: string | null;
  note: string | null;
  answer_key: string | null;
  editable: boolean;
  answer_value: string | null;
};

export type ReviewForm = {
  form_id: string;
  title: string;
  placeholder: boolean;
  official_source?: { url: string; sha256: string; fetched_at: string } | null;
  summary: Record<string, number>;
  warnings: string[];
  fields: ReportRow[];
  preview_url: string;
};

export type SummaryLine = {
  label: string;
  text: string | null;
  citation: { source_url: string; fetched_at: string; content_hash: string; confidence: number; verify_with_authority: boolean } | null;
};

export type Review = {
  forms: ReviewForm[];
  summary: { steps: { order: number; name: string; conditional: boolean; municipal_data_missing: boolean; lines: SummaryLine[] }[] };
  reviewed: boolean;
  consent_statement: string;
};

export type ChecklistItem = {
  order: number;
  licence: string;
  name: string;
  portal_url: string | null;
  authority: string | null;
  fee: string | null;
  timeline: string | null;
  documents: string[];
  actions: string[];
  conditional: boolean;
  renewal_months: number | null;
};
