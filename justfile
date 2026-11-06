set shell := ["powershell.exe", "-NoLogo", "-Command"]

# Launch all ScopeKeeper services with 1 command (Dashboard, Backend, Orchestrator)
demo:
    python scripts/start_demo.py

# Install dependencies and pre-commit hooks
setup:
    cd clerk; uv sync --all-extras

# Generate the demo repo and load seed data
seed:
    python demo-app/seed/seed_history.py
    cd clerk; uv run python -m clerk.cli seed

# Run Clerk backend with reload
dev:
    cd clerk; uv run uvicorn clerk.main:app --reload --port 8080

# Run unit, contract, and integration tests
test:
    cd clerk; uv run pytest
    cd clerk; uv run ruff check src tests
    cd clerk; uv run mypy --strict src tests

# Run classifier evaluation on the 20 fixture asks
eval:
    cd clerk; uv run python ../scripts/eval_classifier.py

# Reset database, open change rooms, git branches, previews, and simulated clock
reset:
    cd clerk; uv run python ../scripts/reset_demo.py

# Trigger evening handover (7:00 PM IST Flip to Scout autopilot)
flip:
    cd clerk; uv run python -m clerk.cli flip

# Trigger morning brief & handover (9:30 AM IST Flip to Priya copilot)
morning:
    cd clerk; uv run python -m clerk.cli morning

# Start Docker Compose stack
up:
    docker compose up --build -d

# Stop Docker Compose stack
down:
    docker compose down
