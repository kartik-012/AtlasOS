# ==============================================================================
# AtlasOS Backend Dockerfile
#
# Multi-stage build for the FastAPI application.
# Stage 1 (builder): Installs Python dependencies into an isolated directory.
# Stage 2 (runtime): Copies only the installed packages and app code.
#
# Why multi-stage:
#   - Reduces final image size by excluding build tools (gcc, libpq-dev).
#   - Separates build-time concerns from runtime concerns.
#   - Produces a smaller, more secure production image.
#
# Security:
#   - Runs as non-root user 'atlasos' (UID 1000).
#   - PYTHONDONTWRITEBYTECODE prevents .pyc file creation.
#   - PYTHONUNBUFFERED ensures log output is not buffered.
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder — Install dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies required by psycopg2-binary and other C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first to leverage Docker layer caching.
# Dependencies are re-installed only when requirements.txt changes.
COPY requirements.txt .
RUN pip install --prefix=/install --no-warn-script-location -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime — Lean production image
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install only runtime dependencies (libpq for psycopg2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 atlasos && \
    useradd --uid 1000 --gid atlasos --shell /bin/bash --create-home atlasos

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R atlasos:atlasos /app

# Copy startup script and make it executable
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Railway injects $PORT dynamically — start.sh expands it via the shell
EXPOSE 8000
CMD ["/start.sh"]
