# =============================================================================
# AtlasOS Inference Microservice – Dockerfile
# =============================================================================
# Multi-stage build that bakes both ML models into the image so cold-start
# in production only needs to load from local disk.
# =============================================================================

# --------------- Stage 1: build dependencies & download models ---------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/models \
    SENTENCE_TRANSFORMERS_HOME=/models

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models so they are cached in the image layer
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"
RUN python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; AutoTokenizer.from_pretrained('roberta-large-mnli'); AutoModelForSequenceClassification.from_pretrained('roberta-large-mnli')"

# --------------- Stage 2: production image -----------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/models \
    SENTENCE_TRANSFORMERS_HOME=/models

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded model weights
COPY --from=builder /models /models

WORKDIR /app
COPY . .

# Run as non-root
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser && \
    chown -R appuser:appuser /app /models
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
