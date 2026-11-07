PY ?= python
.PHONY: setup dev stop test lint eval migrate seed e2e loadtest keygen audit placeholders help

help:
	@echo "setup dev stop test lint eval migrate seed e2e loadtest audit keygen placeholders"

setup: ## install deps, create .env
	cd backend && $(PY) -m pip install -e ".[dev]"
	cd frontend && npm install
	@test -f .env || cp .env.example .env
	@echo "Setup done. Run 'make dev' to start the whole stack."

dev: ## whole stack in Docker (db, redis, api, worker, web) and open http://localhost:3000
	@test -f .env || cp .env.example .env
	docker compose up --build

stop:
	docker compose down

test: ## backend tests (>=80% coverage enforced) + frontend unit tests
	cd backend && $(PY) -m pytest
	cd frontend && npm test

lint: ## ruff, mypy, eslint, tsc
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint && npm run typecheck

eval: ## golden cases + citation coverage + hallucination gate
	cd backend && $(PY) -m evals.run

migrate:
	cd backend && alembic upgrade head

seed: ## load the curated seed rules pack into the KB
	cd backend && $(PY) -m app.kb.seed_loader

e2e: ## Playwright end-to-end (builds the frontend first)
	cd frontend && npm run build && npx playwright test

loadtest: ## see docs/LOAD_TEST.md
	cd backend && locust -f ../scripts/loadtest/locustfile.py --host http://localhost:8000 --headless -u 20 -r 5 -t 60s

audit: ## dependency + SAST scans
	cd backend && pip-audit --skip-editable && bandit -r app -ll -q
	cd frontend && npm audit --audit-level=high

placeholders: ## regenerate the placeholder form PDFs
	cd backend && $(PY) ../scripts/make_placeholder_forms.py

keygen: ## generate a Fernet key for FIELD_ENCRYPTION_KEY
	$(PY) -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
