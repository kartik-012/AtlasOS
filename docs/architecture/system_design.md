# AtlasOS System Architecture

AtlasOS is a production-grade AI Memory Operating System providing hierarchical memory management (working, episodic, semantic) for AI agents, with built-in contradiction detection, compression, and evaluation pipelines.

## 1. High-Level Architecture

The system is composed of several independent services communicating over a shared bridge network, orchestrated by Docker Compose.

- **FastAPI Backend (Port 8000)**: The core API server. Stateless, scalable. Handles authentication, routing, and memory pipeline execution.
- **Celery Workers**: Background task processors. Handlers compression (summarization), evaluation runs, retention sweeps.
- **Celery Beat**: Scheduler for periodic background tasks.
- **PostgreSQL 15 (Port 5432)**: The System of Record. Stores all relational data (tenants, users, episodic/semantic metadata, evaluations, audit logs).
- **Redis 7 (Port 6379)**: Multi-purpose memory store.
  - DB 0: Application Cache & Rate Limiting.
  - DB 1: Celery Message Broker.
  - DB 2: Celery Result Backend.
- **Qdrant (Port 6333, 6334)**: Vector database storing high-dimensional embeddings for semantic search.
- **Next.js Frontend (Port 3000)**: Developer Console for managing tenants, API keys, and exploring memories.

## 2. Core Concepts

### Hierarchical Memory
1. **Working Memory**: Ephemeral task state. Stored in Redis (DB 0) with a 2-hour TTL.
2. **Episodic Memory**: Raw agent experiences and interactions. Stored in PostgreSQL with embeddings in Qdrant.
3. **Semantic Memory**: Consolidated facts derived from episodic memories via background compression or explicit writes.

### Multi-Tenancy & Isolation
AtlasOS is designed for multi-tenancy.
- **Database Level**: PostgreSQL Row-Level Security (RLS) policies enforce isolation. Every request-scoped DB session sets `app.current_tenant_id` via `SET LOCAL`. All tenant-scoped tables use this to filter data automatically.
- **Vector Store Level**: Qdrant queries always filter on a `tenant_id` payload field.
- **Application Level**: Tenant IDs are derived securely from the authenticated context (API key or Session), never from user-supplied parameters.

### Contradiction Detection
When a new semantic memory is written, it is compared against existing memories using a Natural Language Inference (NLI) model (e.g., `roberta-large-mnli`). If a contradiction is detected, a `ContradictionLog` is created, and the system resolves it based on the tenant's configured policy (`most_recent_wins`, `confidence_weighted`, `manual_review`).

### Audit Logging
All critical operations are recorded in an immutable `audit_log` table. Immutability is enforced at the database level using a PostgreSQL trigger that raises an exception on any `UPDATE` or `DELETE` attempt.

## 3. Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x (asyncpg for runtime, psycopg2 for Alembic migrations)
- **Validation**: Pydantic v2
- **Task Queue**: Celery
- **Database**: PostgreSQL 15
- **Vector DB**: Qdrant 1.8.4
- **Cache/Broker**: Redis 7
- **Logging**: structlog
- **Linting/Formatting**: ruff, mypy

## 4. Phase 1 Accomplishments
- Project scaffolding and dependency locking.
- Docker Compose orchestration.
- Configuration management (Pydantic BaseSettings).
- Database connection pooling (AsyncEngine, Session factories).
- Redis client and key namespace builder.
- Exception hierarchy.
- Structured logging (JSON/Console).
- Complete SQLAlchemy schema definition (18 models).
- Alembic environment setup and initial schema migration (including RLS, Triggers, and Indexes).
- Qdrant initialization script.
