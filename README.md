# doc-pipeline-orchestrator

A Django-based orchestration layer that wraps two existing AI/ML pipelines and exposes them through a unified web interface. Upload PDFs, watch real-time processing progress, and ask questions across all processed documents via a chat interface.

---

## What it does

1. **Upload** — user drops one or more PDF files into the frontend
2. **Process** — a Celery worker calls two upstream services in sequence:
   - `pdf-extraction-service` extracts structured fields using the Gemini API
   - `rag-search-service` chunks, embeds, and indexes the text into pgvector
3. **Watch** — the browser receives live step-by-step progress via Server-Sent Events (SSE)
4. **Ask** — user types a question; Django calls `rag-search-service` and streams the answer back

---

## Architecture

```
[ React + Vite frontend ]
        |
        | POST /api/upload/      → creates Job row, enqueues Celery task
        | GET  /api/events/<id>/ → SSE stream (live progress)
        | GET  /api/status/<id>/ → polling fallback
        | GET  /api/jobs/        → job list on page load
        | POST /api/ask/         → synchronous Q&A
        |
[ Django REST Framework ]
        |                   \
        | enqueue             \  POST /search → rag-search-service
        ↓                      \
[ Redis ]  ← Celery broker        [ rag-search-service ]
           ← Pub/Sub channel
        ↓
[ Celery worker ]
        | ① POST /extract → pdf-extraction-service
        | ② POST /ingest/document → rag-search-service
        ↓
[ PostgreSQL ]  ← Job rows (status, result_json)
```

### Upstream services (already exist — not modified)

| Service | Repo | Host port | What it does |
|---|---|---|---|
| `pdf-extraction-service` | `pdf_2_structured_data_LLM_ETL_pipeline` | 8001 | Extracts structured fields from PDFs via Gemini API |
| `rag-search-service` | `arxiv-rag` | 8002 | Chunks, embeds, indexes documents into pgvector; answers semantic search queries |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Django 4.2 + Django REST Framework |
| Task queue | Celery 5.3 |
| Message broker | Redis 7 |
| SSE / async | `redis.asyncio`, Django async views |
| Database | PostgreSQL 16 + pgvector |
| Frontend | Vite + React 18 + TypeScript *(Phase 5)* |
| Containerisation | Docker Compose |
| CI/CD | GitHub Actions — pytest + ruff *(Phase 6)* |
| AI | Gemini API (via upstream services) |
| Python | 3.11 |

---

## Prerequisites

- Docker and Docker Compose
- Both upstream repos cloned as siblings of this repo:
  ```
  dhu/
  ├── doc-pipeline-orchestrator/   ← this repo
  ├── pdf_2_structured_data_LLM_ETL_pipeline/
  └── arxiv-rag/
  ```
- A `.env` file in the project root (see `.env.example`)

---

## Getting started

```bash
# 1. Copy and fill in the environment file
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Run Django migrations
docker compose exec orchestrator python manage.py migrate

# 4. Open the frontend
# http://localhost:8000 (Django API)
# http://localhost:5173 (Vite dev server — after Phase 5)
```

---

## API endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/upload/` | Upload a PDF; returns `Job` with `id` and `status: QUEUED` |
| `GET` | `/api/events/<id>/` | SSE stream — pushes `PROCESSING`, `extracted`, `DONE`, `FAILED` events |
| `GET` | `/api/status/<id>/` | Polling fallback — returns current `Job` row |
| `GET` | `/api/jobs/` | List all jobs, newest first |
| `POST` | `/api/ask/` | Body `{"question": str}` — returns answer and sources from rag-search-service |

### Job status lifecycle

```
QUEUED → PROCESSING → DONE
                    ↘ FAILED
```

### SSE event format

```
data: {"status": "PROCESSING", "step": "started"}

data: {"status": "PROCESSING", "step": "extracted"}

data: {"status": "DONE"}

data: {"status": "FAILED", "error": "..."}
```

---

## Development commands

```bash
# Run tests
docker compose exec orchestrator pytest

# Run tests with output
docker compose exec orchestrator pytest -v

# Lint
docker compose exec orchestrator ruff check .

# Open Django shell
docker compose exec orchestrator python manage.py shell

# Watch Celery worker logs
docker compose logs -f celery-worker
```

---

## Project structure

```
doc-pipeline-orchestrator/
├── orchestrator/          # Django project settings, URLs, Celery app
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── jobs/                  # Django app — core logic
│   ├── models.py          # Job model
│   ├── views.py           # REST endpoints + async SSE view
│   ├── tasks.py           # Celery task: process_pdf
│   ├── serializers.py     # DRF serializer for Job
│   ├── urls.py            # App-level routing
│   └── tests.py           # 12 pytest tests
├── frontend/              # React + Vite (Phase 5)
├── docs/
│   └── progress/          # Per-phase build notes and lessons learned
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Build phases

| Phase | Description | Status |
|---|---|---|
| 0 | Add `/ingest/document` to `rag-search-service` | Done |
| 1 | Scaffold — Docker Compose, settings, requirements | Done |
| 2 | Django `Job` model and migration | Done |
| 3 | REST endpoints with polling | Done |
| 4 | Celery task `process_pdf` | Done |
| 4.5 | SSE upgrade — Redis Pub/Sub + async stream view | Done |
| 5 | React frontend | In progress |
| 6 | GitHub Actions CI | Pending |
