# Backend — whatdidimiss

FastAPI + Celery backend for AI-powered YouTube content coaching.

## Prerequisites

- Python 3.12+
- PostgreSQL 16
- Redis 7
- Google Cloud project (Video Intelligence API, Cloud Storage, OAuth, YouTube Data/Analytics APIs)
- OpenAI API key

## Quick Start (Docker)

```bash
# Start Postgres + Redis + API + Celery worker
docker compose up
```

This runs everything on:
- API: http://localhost:8000
- Postgres: localhost:5432
- Redis: localhost:6379

## Quick Start (Local)

```bash
# Create venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Copy and fill in env
cp .env.example .env
# Edit .env with your credentials

# Start Postgres + Redis (if not using Docker)
docker compose up db redis -d

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg driver) |
| `REDIS_URL` | Redis connection for Celery |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCS_BUCKET_NAME` | GCS bucket for video storage |
| `OPENAI_API_KEY` | OpenAI API key |
| `SECRET_KEY` | JWT signing key |
| `FERNET_KEY` | Token encryption key (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `AUTH_DISABLED` | Set `true` to skip OAuth in dev (creates a dev user) |

## Database Migrations

```bash
# Run all pending migrations
.venv/bin/alembic upgrade head

# Create a new migration (use timestamp naming)
.venv/bin/alembic revision --autogenerate -m "$(date +%s)_description"
```

Never edit existing migrations — always create new ones.

## Build Check

```bash
# Verify all Python files compile
python3 -m py_compile app/main.py
```

## Project Structure

```
app/
  api/v1/          # FastAPI route handlers
  models/          # SQLAlchemy models
  schemas/         # Pydantic request/response schemas
  services/        # Business logic (YouTube, GCS, OpenAI, etc.)
  workers/         # Celery tasks (video processing pipeline)
  prompts/         # GPT-4o system/user prompts
  utils/           # Exceptions, helpers
  config.py        # Settings from .env
  main.py          # FastAPI app setup
  dependencies.py  # DI (get_db, get_current_user)
alembic/           # Database migrations
```
