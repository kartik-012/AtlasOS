from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> Any:
    """
    WebSocket endpoint for real-time events.
    """
    await websocket.accept()
    settings = get_settings()
    
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    try:
        await pubsub.subscribe("atlasos_events")
        logger.info("WebSocket connected, subscribed to atlasos_events")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error("Failed to send message to websocket client", error=str(e))
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.exception("WebSocket error", error=str(e))
    finally:
        await pubsub.unsubscribe("atlasos_events")
        await redis_client.aclose()
