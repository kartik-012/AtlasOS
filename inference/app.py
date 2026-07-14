"""
AtlasOS AI Inference Microservice

Production-grade FastAPI microservice serving:
  - /v1/embeddings : OpenAI-compatible text embedding via BAAI/bge-large-en-v1.5
  - /v1/nli        : Natural Language Inference via roberta-large-mnli
  - /health        : Readiness / liveness probe
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

import torch
import torch.nn.functional as F
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-large-en-v1.5")
NLI_MODEL_NAME = os.getenv("NLI_MODEL_NAME", "roberta-large-mnli")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global model registry – populated once during startup
# ---------------------------------------------------------------------------
models: dict = {}


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models once at startup and release on shutdown."""

    # -- Embedding model --
    logger.info("Loading embedding model: %s (device=%s) …", EMBEDDING_MODEL_NAME, DEVICE)
    models["embedding"] = SentenceTransformer(EMBEDDING_MODEL_NAME, device=DEVICE)
    logger.info("Embedding model loaded successfully.")

    # -- NLI model + tokenizer --
    logger.info("Loading NLI model: %s (device=%s) …", NLI_MODEL_NAME, DEVICE)
    models["nli_tokenizer"] = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
    models["nli_model"] = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME).to(DEVICE)
    models["nli_model"].eval()
    logger.info("NLI model loaded successfully.")

    yield  # ---- application is running ----

    # Cleanup
    models.clear()
    logger.info("Models unloaded.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AtlasOS Inference Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class EmbeddingRequest(BaseModel):
    input: List[str]
    model: Optional[str] = EMBEDDING_MODEL_NAME


class EmbeddingObject(BaseModel):
    embedding: List[float]


class EmbeddingUsage(BaseModel):
    total_tokens: int


class EmbeddingResponse(BaseModel):
    data: List[EmbeddingObject]
    model: str
    usage: EmbeddingUsage


class NLIRequest(BaseModel):
    premise: str
    hypothesis: str


class NLIResponse(BaseModel):
    contradiction: float
    entailment: float
    neutral: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Generate normalised embeddings for a batch of input texts."""
    try:
        embedding_model: SentenceTransformer = models["embedding"]

        with torch.no_grad():
            embeddings = embedding_model.encode(
                request.input,
                normalize_embeddings=True,
                batch_size=len(request.input),
                convert_to_numpy=True,
            )

        # Rough token count – whitespace split as a fast proxy
        total_tokens = sum(len(text.split()) for text in request.input)

        return EmbeddingResponse(
            data=[EmbeddingObject(embedding=emb.tolist()) for emb in embeddings],
            model=request.model or EMBEDDING_MODEL_NAME,
            usage=EmbeddingUsage(total_tokens=total_tokens),
        )
    except Exception as exc:
        logger.exception("Embedding inference failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/nli", response_model=NLIResponse)
async def predict_nli(request: NLIRequest):
    """Predict textual entailment between a premise and hypothesis."""
    try:
        tokenizer = models["nli_tokenizer"]
        nli_model = models["nli_model"]

        inputs = tokenizer(
            request.premise,
            request.hypothesis,
            return_tensors="pt",
            truncation=True,
        ).to(DEVICE)

        with torch.no_grad():
            logits = nli_model(**inputs).logits

        # roberta-large-mnli label order: 0=contradiction, 1=neutral, 2=entailment
        probs = F.softmax(logits, dim=-1).squeeze().tolist()

        return NLIResponse(
            contradiction=probs[0],
            neutral=probs[1],
            entailment=probs[2],
        )
    except Exception as exc:
        logger.exception("NLI inference failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health():
    """Readiness probe – confirms both models are loaded."""
    embedding_status = "loaded" if "embedding" in models else "not_loaded"
    nli_status = "loaded" if "nli_model" in models else "not_loaded"

    return {
        "status": "healthy" if embedding_status == "loaded" and nli_status == "loaded" else "degraded",
        "models": {
            "embedding": embedding_status,
            "nli": nli_status,
        },
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080)
