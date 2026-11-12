# Contributing to Red Tape Navigator

Thank you for wanting to help. Please read this page before you open an issue or a pull request.

## Who can contribute

This repository is **proprietary** (see [LICENSE](LICENSE)). It is public to view only. Code, data and other materials may be changed only by **Team Onyx** and people the owner has **approved in writing** (a GitHub invitation counts). If you are not one of them, you are still welcome to:

- report a bug, a wrong rule, a broken link or an accessibility barrier (use the issue forms);
- suggest an improvement;
- tell us about a security problem, privately (see [SECURITY.md](SECURITY.md)).

Please do not copy, fork for reuse, or redistribute the project.

## Before you start

1. Read the [README](README.md), then the [developer guide](docs/DEVELOPER_GUIDE.md) (architecture, phases, configuration, lessons learned).
2. Check the [open items](docs/LAUNCH_CHECKLIST.md) so you do not repeat work.
3. Open or comment on an issue before starting anything large.

## Ground rules that protect users

These come from the product's promises and are not negotiable:

- **A human always submits.** No code path may submit anything to a government portal. A test enforces this.
- **Never invent legal facts.** Every fee, timeline, authority and document list must come from an official page you actually read, and be recorded in [`docs/RULES_VERIFICATION.md`](docs/RULES_VERIFICATION.md). If you cannot read the source, say so.
- **Keep personal data safe.** Never commit secrets, `.env` files, databases, keys or real Aadhaar, PAN, bank or contact details. Use obviously fake test values.
- **Do not bypass protections.** No CAPTCHA solving, firewall evasion, or scraping outside the approved domain list.
- **Do not use the State Emblem of India** beyond what is already in the team logo and recorded in the launch checklist.
- **No billing.** The product is free for everyone; a test guards this.
- Do not add a dependency bot configuration (`.github/dependabot.yml`); it once opened many unwanted pull requests.

## Set up

Follow **Quick start → Installation and setup** in the [README](README.md). In short:

```bash
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cd ../frontend && npm ci
```

## Make a change

1. Create a branch from `main` (for example `fix/trade-licence-fee-kolkata`).
2. Keep the change small and focused. One topic per pull request.
3. Add or update tests. Backend coverage must stay at or above 80% (it is about 95% now).
4. Update the docs in the same pull request: the README, `docs/LAUNCH_CHECKLIST.md`, `docs/RULES_VERIFICATION.md` when rules change, and translations.
5. Run the checks below and paste the real results in the pull request.

### Checks to run

```bash
cd backend && ruff check . && mypy app && python -m pytest && python -m evals.run && python ../scripts/rule_freshness.py --strict
cd ../frontend && npm run lint && npm run typecheck && npm test && npm run build
cd frontend && npx playwright test            # needs ports 3000 and 8000 free
```

Continuous integration runs the same checks (7 jobs). A pull request cannot be merged while a job fails.

### Adding or changing rules

- Add a business type, licence or city following the table in the developer guide (section 9, "How to extend the product").
- Every rule needs a source URL and a note in `docs/RULES_VERIFICATION.md`.
- Add the Hindi and Bengali text in the same change; tests fail if a translation is missing.

### Style

- Python: `ruff` and `mypy` clean, type hints on public functions, line length 130.
- TypeScript: `eslint` and `tsc` clean. Interface text goes in `frontend/messages/{en,hi,bn}.json`, never hard-coded.
- Write documentation in plain language. Prefer short sentences and concrete examples.

## Commit messages

Use a short imperative summary of what changed and why, for example `fix: Surat shops-and-establishments fee from the official schedule`.

## Reviews

The owner reviews and approves every change (see `.github/CODEOWNERS`). Please be patient and respond to review comments politely, as described in the [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

See [SUPPORT.md](SUPPORT.md).
