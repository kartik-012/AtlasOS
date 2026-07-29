from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.dependencies import (
    get_db_session_no_tenant,
    require_role,
)
from app.core.logging import get_logger
from app.schemas.system import SystemStatsResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System"])


@router.get("/stats", response_model=SystemStatsResponse, dependencies=[Depends(require_role("admin"))])
async def get_system_stats(
    db: AsyncSession = Depends(get_db_session_no_tenant),
) -> Any:
    """Return system stats."""
    pass

@router.get("/usage", tags=["System"], description="Returns time-series usage data for analytics")
async def get_system_usage(
    db: AsyncSession = Depends(get_db_session_no_tenant),
) -> Any:
    """Return mock analytics data."""
    import random
    from datetime import datetime, timedelta
    
    data = []
    base_date = datetime.now() - timedelta(days=30)
    for i in range(30):
        current_date = base_date + timedelta(days=i)
        data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "requests": random.randint(1000, 5000),
            "storage_mb": random.randint(100, 1000),
            "tokens": random.randint(50000, 200000)
        })
    return data
