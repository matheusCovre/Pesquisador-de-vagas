PYTHON ?= .venv/bin/python

.PHONY: up down ps logs restart db-migrate install-dev test coverage lint format check

install-dev:
	cd backend && $(PYTHON) -m pip install -r requirements-dev.txt

test:
	cd backend && $(PYTHON) -m pytest

coverage:
	cd backend && $(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html

lint:
	cd backend && $(PYTHON) -m ruff check .
	cd backend && $(PYTHON) -m ruff format --check .

format:
	cd backend && $(PYTHON) -m ruff check --fix .
	cd backend && $(PYTHON) -m ruff format .

check: lint test

up:
	npx --yes supabase --workdir database start
	$(MAKE) db-migrate
	docker compose up -d --build

db-migrate:
	npx --yes supabase --workdir database migration up

down:
	docker compose down
	npx --yes supabase --workdir database stop

ps:
	docker compose ps
	npx --yes supabase --workdir database status

logs:
	docker compose logs -f

restart: down up
