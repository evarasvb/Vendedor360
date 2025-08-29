.PHONY: install dev run test lint format up down migrate head alembic-init

PYTHON=python3
PIP=pip3
APP_DIR=metaops

install:
	$(PIP) install -r requirements.txt

run:
	uvicorn metaops.app.main:app --host 0.0.0.0 --port 8000 --reload

lint:
	ruff check $(APP_DIR) tests

format:
	ruff format $(APP_DIR) tests

test:
	pytest -q

up:
	docker compose up --build

down:
	docker compose down -v

alembic-init:
	alembic init alembic

migrate:
	alembic revision --autogenerate -m "auto"

head:
	alembic upgrade head