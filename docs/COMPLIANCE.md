# DPDP Act 2023 compliance checklist

Status legend: ✅ implemented in code · 🟡 implemented but needs organisational action · ⛔ not implemented / out of scope.
This is an engineering checklist, **not legal advice**. A qualified lawyer must review it before any pilot.

## Roles
The deployer is the **Data Fiduciary**. Citizens are **Data Principals**. A CSC operator acting for a citizen is a
processor/assistant under the fiduciary's instructions (their sessions and consents are logged under their own account;
document the arrangement in the operator agreement). Anthropic's API (when enabled) and the cloud host are sub-processors.

## Checklist

| Requirement | Status | Where / how |
|---|---|---|
| **Notice** in clear language, with purposes and rights | ✅ | `GET /consent/notice`; consent screen (en/bn/hi) lists purposes, data, retention, rights |
| **Free, specific, informed, unambiguous consent**, separate per purpose | ✅ | Purposes `service` (required) and `reminders` (optional, unticked by default). Sessions cannot be created without `service` consent (403) |
| **Consent log** (who, what, which policy version, when) | ✅ | `consents` table, append-only per grant/withdrawal; `GET /consent`; policy version recorded |
| **Withdraw consent** as easy as giving it | ✅ | `POST /consent {granted:false}`; reminders stop being scheduled (checked at use) |
| **Purpose limitation / data minimisation** | ✅ | Only fields required by the chosen forms are requested (union of template `required` sources); eval gate checks that e.g. a tailoring shop is never asked for food details |
| **Accuracy / correction** | ✅ | Every answer is editable; review step; validators (PAN, Aadhaar checksum, PIN, mobile, IFSC, dates) |
| **Storage limitation + auto purge** | ✅ | `RETENTION_DAYS` (default 90) sets `expires_at`; `purge_job` runs daily (Arq) and `POST /admin/purge`; deletes answers, reminders, review items, sessions |
| **Right to access / portability** | ✅ | `GET /privacy/export` (JSON with all answers in full, consents, reminders) |
| **Right to erasure** | ✅ | `DELETE /privacy/me` (account + all session data; email anonymised, tokens revoked), `DELETE /privacy/sessions/{id}` |
| **Security safeguards** | ✅ | Field-level Fernet encryption of Aadhaar / PAN / bank account (key rotation supported), TLS at the edge, RBAC, rate limiting, redacted logs, hash-chained audit log, secrets via env/secret manager. See [SECURITY.md](SECURITY.md) |
| **Breach notification process** | 🟡 | Runbook has the incident steps; the organisation must register with and be ready to notify the Data Protection Board and affected principals |
| **Grievance redressal** | 🟡 | `GET /privacy/policy` points to the DPO contact; the deployer must appoint a contact and SLA |
| **Children's data** | ✅/🟡 | Date-of-birth validator rejects applicants under 18. The product is for adults; the deployer must keep that in the notice |
| **Cross-border transfer** | 🟡 | `DATA_REGION` flag + Terraform default `ap-south-1`. The LLM call leaves the region unless an in-region model endpoint is used. **What is sent to the LLM:** the goal sentence and scraped public pages only. **Aadhaar, PAN, bank details and interview answers are never sent to the LLM.** |
| **Significant Data Fiduciary duties** (DPO, DPIA, audit) | ⛔ | Depends on notification by the Government; do a DPIA before the pilot (template in PILOT_PLAN) |
| **Aadhaar-specific rules** (Aadhaar Act, UIDAI) | 🟡 | We store an Aadhaar number only because the chosen forms ask for it, encrypted and masked in UI/logs. Before production, decide whether to use a UIDAI-approved masked/virtual-ID flow instead; get legal sign-off |

## Data inventory

| Data | Why | Where | Protection | Retention |
|---|---|---|---|---|
| Email, password hash, language | account | `users` | bcrypt; email anonymised on erasure | until erasure |
| Goal text, parsed fields | service | `nav_sessions` | access control | `RETENTION_DAYS` |
| Form answers | fill forms | `answers` | sensitive ones encrypted (Fernet/MultiFernet) | `RETENTION_DAYS` |
| Consents | legal record | `consents` | append-only | kept (legal record), no PII beyond user id |
| Audit log | accountability | `audit_log` | hash-chained, PII redacted, never contains answer values | kept per org policy |
| Reminder destination (email / mobile) | send reminders | `reminders` | access control | deleted with the session |

## Data residency
Set `DATA_REGION` to document the deployment region (surfaced at `/ready`). Deploy the database, Redis and API in an
Indian region (Terraform default `ap-south-1` Mumbai; `ap-south-2` Hyderabad is an alternative). Backups stay in-region.
Egress to the LLM provider is the main residency question; options are an in-region hosted endpoint, or running with
`ANTHROPIC_API_KEY` unset (deterministic mode, no LLM egress). Decide with counsel.

## Pre-pilot actions (organisational)
1. Appoint DPO / grievance officer; publish privacy policy matching `GET /consent/notice`.
2. Complete a DPIA; sign processor agreements (cloud, LLM provider, CSC operators).
3. Legal review of storing Aadhaar numbers; prefer not collecting if a form can accept masked IDs.
4. Penetration test and security audit of the deployed environment.
5. Breach-response tabletop exercise using the runbook.
