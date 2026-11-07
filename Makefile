PY ?= python
.PHONY: setup dev test lint eval migrate seed keygen
setup:
	cd backend && $(PY) -m pip install -e ".[dev]" && cd ../frontend && npm install
	@test -f .env || cp .env.example .env
keygen:
	$(PY) -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
dev:
	docker compose up --build
test:
	cd backend && $(PY) -m pytest
lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint && npx tsc --noEmit
eval:
	cd backend && $(PY) -m evals.run
migrate:
	cd backend && alembic upgrade head
seed:
	cd backend && $(PY) -m app.kb.seed_loader
