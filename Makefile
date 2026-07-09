# Qurator — quantum index tuning advisor. Common tasks.
.DEFAULT_GOAL := help
PY := backend/.venv/bin/python
UV := uv

.PHONY: help db seed setup probe solve bench quantum cache api dev test reset up down clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

db: ## start Postgres + HypoPG (host port 5433)
	docker compose up -d --build db

setup: ## create the backend venv and install deps (Python 3.12)
	cd backend && $(UV) venv --python 3.12 && $(UV) pip install -e ".[dev,quantum]"

seed: ## seed the demo fintech dataset (2M transactions, deterministic)
	cd backend && .venv/bin/python -m qurator.cli seed

probe: ## measure candidate index benefits (HypoPG)
	cd backend && .venv/bin/python -m qurator.cli probe

solve: ## classical baselines: greedy vs exact vs simulated annealing
	cd backend && .venv/bin/python -m qurator.cli solve

bench: ## apply greedy/exact index sets for real and measure latency
	cd backend && .venv/bin/python -m qurator.cli bench

quantum: ## run the full quantum pipeline (probe -> QUBO -> QAOA)
	cd backend && .venv/bin/python -m qurator.cli quantum

cache: ## regenerate the demo artifact and sync it to the frontend
	cd backend && .venv/bin/python -m qurator.cli cache
	cp backend/cache/demo_run.json frontend/public/demo_run.json

reset: ## drop all qur_* indexes (restore clean baseline)
	cd backend && .venv/bin/python -m qurator.cli reset

api: ## run the FastAPI backend (port 8088)
	cd backend && .venv/bin/uvicorn qurator.api:app --port 8088 --reload

dev: ## run the Next.js frontend (port 3000/3001)
	cd frontend && npm run dev

test: ## run the backend test suite
	cd backend && .venv/bin/python -m pytest -q

up: ## db + backend API in Docker (full stack)
	docker compose --profile full up -d --build

down: ## stop all containers
	docker compose --profile full down

clean: ## stop containers and remove the database volume
	docker compose --profile full down -v
