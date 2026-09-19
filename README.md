# doc-pipeline-orchestrator

Django service that orchestrates two AI backends — PDF structured extraction and RAG-based semantic search — behind a unified REST API, letting users upload documents and query them in natural language without managing the underlying pipeline complexity. Uploads are processed asynchronously via Celery; the browser receives live progress over a Redis Pub/Sub SSE stream. Completed documents can be queried or summarised on demand via the Gemini API.

---

## Architecture

```
[ React + Vite frontend ]
        |
        | POST /api/upload/          → creates Job row, enqueues Celery task
        | GET  /api/events/<id>/     → SSE stream (Redis Pub/Sub)
        | GET  /api/status/<id>/     → polling fallback
        | GET  /api/jobs/            → job list, newest first
        | POST /api/ask/             → semantic search across all indexed documents
        | POST /api/summarise/<id>/  → enqueue AI summary generation
        |
[ Django REST Framework ]
        |                        \
        | enqueue                  \  POST /search → rag-search-service
        ↓                           \
[ Celery + Redis ]                    [ rag-search-service :8002 ]
        |
        | process_pdf:
        | ① POST /extract          → pdf-extraction-service :8001
        | ② POST /ingest/document  → rag-search-service :8002
        |
        | summarise_job:
        | ① GET /results/<id>      → pdf-extraction-service :8001
        | ② Gemini API             → plain-English summary stored on Job row
        ↓
[ PostgreSQL ]      ← Job rows (status, result_json, summary, error)
[ S3 / LocalStack ] ← uploaded PDF storage (Terraform-provisioned)
```

### Upstream services

| Service | Port | Role |
|---|---|---|
| `pdf-extraction-service` | 8001 | Structured field extraction from PDFs via Gemini API |
| `rag-search-service` | 8002 | Document chunking, embedding, pgvector indexing, semantic search |

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework, Python 3.11 |
| Task queue | Celery 5.3, Redis 7 |
| SSE / async | `redis.asyncio`, Django async views |
| Database | PostgreSQL 16 + pgvector |
| Storage | AWS S3 (LocalStack for local dev), Terraform IaC |
| Frontend | React 18, Vite, TypeScript |
| AI | Gemini API |
| Containerisation | Docker Compose (8 services: orchestrator, Celery worker, PostgreSQL, Redis, pdf-extraction-service, rag-search-service, frontend, LocalStack) |
| CI | GitHub Actions — ruff + pytest on every push |

---

## Getting started

```bash
# Clone this repo and both upstream services as siblings
git clone https://github.com/dingzehu/doc-pipeline-orchestrator
git clone https://github.com/dingzehu/pdf_2_structured_data_LLM_ETL_pipeline
git clone https://github.com/dingzehu/arxiv-rag

# Copy and fill in environment variables
cp .env.example .env

# Start all services
docker compose up --build

# Run migrations
docker compose exec orchestrator python manage.py migrate

# Provision S3 bucket (LocalStack must be healthy)
cd terraform && tflocal init && tflocal apply

# Frontend:   http://localhost:5173
# Django API: http://localhost:8000
```

---

## API

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/upload/` | Upload a PDF; returns `Job` with `id` and `status: QUEUED` |
| `GET` | `/api/events/<id>/` | SSE stream — real-time job progress |
| `GET` | `/api/status/<id>/` | Polling fallback |
| `GET` | `/api/jobs/` | List all jobs, newest first |
| `POST` | `/api/ask/` | `{"question": str}` — answer + sources |
| `POST` | `/api/summarise/<id>/` | Enqueue AI summary for a completed job |

### Job lifecycle

```
QUEUED → PROCESSING → DONE
                    ↘ FAILED
```

### SSE events

```
data: {"status": "PROCESSING", "step": "started"}
data: {"status": "PROCESSING", "step": "extracted"}
data: {"status": "DONE"}
data: {"status": "FAILED", "error": "..."}
```

---

## Infrastructure

The `terraform/` directory provisions the S3 bucket used for PDF storage. Configured for LocalStack locally; switching to real AWS requires removing the `skip_*` provider flags and supplying real credentials via environment variables.

---

## Tests

```bash
docker compose exec orchestrator pytest -v
docker compose exec orchestrator ruff check .
```

12 tests across all endpoints and the `process_pdf` Celery task. All upstream HTTP calls are mocked at the service boundary. CI runs against a real PostgreSQL 16 container on every push.

Coverage:
- `UploadView` — success, missing file, storage failure (`OSError` → `FAILED`)
- `StatusView` — success, 404 on unknown ID
- `JobListView` — newest-first ordering
- `AskView` — success, missing question, upstream 502
- `process_pdf` — success, extraction failure, ingestion failure

---

## Project structure

```
doc-pipeline-orchestrator/
├── orchestrator/        # Django settings, Celery app, root URLs
├── jobs/
│   ├── models.py        # Job model
│   ├── views.py         # REST endpoints + async SSE view
│   ├── tasks.py         # process_pdf + summarise_job Celery tasks
│   ├── serializers.py
│   ├── urls.py
│   └── tests.py
├── frontend/            # React + Vite + TypeScript
├── terraform/           # S3 bucket IaC
├── .github/workflows/   # CI pipeline
└── docker-compose.yml   # 8 services
```
