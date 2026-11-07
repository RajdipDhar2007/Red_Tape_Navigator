# 5-minute demo script

Setup (before the audience arrives): `make setup && make dev`, open <http://localhost:3000>. Have a second tab ready
at <http://localhost:8000/docs>. Tell the audience up front: **"This is demo mode. Data is local, DigiLocker / e-Sign /
WhatsApp are simulated, and the forms are placeholders."** (The yellow banner says the same.)

| Time | Do | Say / point out |
|---|---|---|
| 0:00 | Landing page. Click **Use a demo account**. | "Auth is JWT with rotating refresh tokens; roles for citizen, CSC operator, reviewer, admin." |
| 0:30 | **Consent screen**: read one line aloud, leave reminders unticked, click *I agree and continue*. | "DPDP: purpose-specific, separately logged consent. Nothing is processed before this." |
| 0:50 | Click **Try the demo: bakery in Kolkata** (or type it; try the 🎤 button). | "Plain-language goal. The agent extracted: activity = bakery, city = Kolkata, state = West Bengal. If the city were missing it would ask exactly one question." |
| 1:10 | **Checklist** appears. Scroll through Udyam → FSSAI → Trade licence → Fire NOC → Shops & Est. → GST. | "Ordered by dependency. Every fee, timeline and document line has a source link, a *checked* date, a confidence and a content hash. Anything the system is unsure about says **Verify with the authority** and is queued for a human reviewer." Hover a `#hash`. |
| 1:50 | Click **Start the interview**. Answer the first two questions (name, father's name). | "It computed the union of fields across all three forms and asks only what's missing, one or two at a time. Name is asked once and reused on every form." |
| 2:20 | Type `12345` as a name → error. Then click the language switcher → **বাংলা**. | "Validation in the user's language. The whole UI and every interview question exist in English, Bengali and Hindi." Switch back. |
| 2:40 | At the PAN/Aadhaar question: enter an invalid PAN, then a valid one (`ABCPE1234F`). Click **Skip for now** on one other question. | "Aadhaar and PAN are encrypted at rest and never logged. Skip, resume and edit are supported." Fast-forward by answering the rest (have the answers in a note). |
| 3:20 | **Go to review.** Left: PDF preview. Right: fields with status badges. | "Side by side. Each field shows where its value came from — *user answer*, *derived from your goal*, or *document*. Missing or doubtful fields are flagged, never guessed. Non-English text is flagged because the official PDF needs English letters." |
| 3:50 | Edit a value (e.g. the business name) → **Save**; the preview refreshes. Show the plain-language summary with citations below. Point at the red *placeholder* note. | "Edits flow back into memory and all forms update. Real forms drop in via JSON field maps." |
| 4:15 | Try ticking nothing: the **I have reviewed this** button is disabled. Tick the consent box, click it. | "Explicit consent. Until now no PDF can be downloaded and no e-Sign can run — the API returns 403. And any later edit invalidates the review." |
| 4:30 | **Ready to sign and submit**. Click **Download PDF**. Click **Try e-Sign (demo)** and point at the label. Show the submission checklist. | "The e-Sign is simulated and labelled as not legally valid. There is **no button and no API** that submits to a government portal. The citizen logs in, solves the captcha, pays, and submits. We only hand over a checklist." |
| 4:50 | Open `/docs` or the terminal: `make eval` result and the audit chain. | "26 golden cases, 100 % citation coverage, zero hallucinations gate in CI; hash-chained audit log; DPDP export and erase endpoints." |

## Backup moves
* If asked "does it use an LLM?": yes when `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` are set (intake gap-filling and live
  extraction with verbatim-quote grounding); without them a deterministic fallback runs and the UI says so.
* If asked about prompt injection: show `docs/SECURITY.md` — domain allowlist in code, untrusted-content delimiters,
  grounding rule, no tool that acts on the world.
* If asked "what's real?": README table. Seed data, mocked integrations, placeholder forms — all labelled.

## Reset
Use a new demo account (each is isolated). To wipe everything: `docker compose down -v`.
