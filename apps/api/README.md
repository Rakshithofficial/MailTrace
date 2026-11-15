# MailTrace API

This directory contains the MailTrace API, database foundation, email intake, deterministic analysis pipeline, optional enrichment/explanation adapters, relationship matching, recommendations, and report generation.

## Local setup

From `apps/api`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

SQLite is the default development database. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL for the fuller environment.

Start the API with:

```powershell
py -m uvicorn main:app --reload --port 8000
```

## Migration commands

```powershell
alembic upgrade head
alembic current
alembic history
alembic downgrade base
```

## Tests

```powershell
pytest
```

The seed helper inserts only controlled synthetic metadata and a quarantined raw-content reference. It never stores secrets or executes uploaded content.
