"""
AtlasOS Knowledge Graph Service.

Orchestrates entity extraction, triple parsing, and Knowledge Graph updates.
"""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.repositories.graph import EntityGraphRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class EntityGraphService:
    """
    Service for extracting knowledge graph triples and updating entity mesh.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._graph_repo = EntityGraphRepository(session)

    async def extract_and_store_triples(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        text: str,
        source_memory_id: uuid.UUID | None = None,
        source_memory_type: str | None = None,
    ) -> list[tuple[str, str, str]]:
        """
        Extract Subject-Predicate-Object triples and store them in the graph.
        """
        triples = self._extract_heuristic_triples(text)
        if not triples:
            return []

        for subj, pred, obj in triples:
            try:
                subj_node = await self._graph_repo.upsert_node(
                    tenant_id=tenant_id,
                    external_user_id=external_user_id,
                    name=subj,
                    entity_type="CONCEPT" if subj.lower() != "user" else "PERSON",
                )
                obj_node = await self._graph_repo.upsert_node(
                    tenant_id=tenant_id,
                    external_user_id=external_user_id,
                    name=obj,
                    entity_type="CONCEPT",
                )
                await self._graph_repo.add_relation(
                    tenant_id=tenant_id,
                    source_node_id=subj_node.id,
                    target_node_id=obj_node.id,
                    relation_type=pred,
                    weight=1.0,
                    source_memory_id=source_memory_id,
                    source_memory_type=source_memory_type,
                )
            except Exception as e:
                logger.warning(
                    "graph_triple_ingest_failed",
                    subj=subj,
                    pred=pred,
                    obj=obj,
                    error=str(e),
                )

        logger.info(
            "triples_stored",
            tenant_id=str(tenant_id),
            count=len(triples),
        )
        return triples

    def _extract_heuristic_triples(self, text: str) -> list[tuple[str, str, str]]:
        """
        Extract Subject-Predicate-Object triples using regex rules.
        Handles key phrases like:
        - "User prefers X" -> ("User", "PREFERS", "X")
        - "User works at X" -> ("User", "WORKS_AT", "X")
        - "User lives in X" -> ("User", "LIVES_IN", "X")
        - "User likes/dislikes X" -> ("User", "LIKES/DISLIKES", "X")
        - "X is a Y" -> ("X", "IS_A", "Y")
        """
        triples: list[tuple[str, str, str]] = []
        patterns = [
            (r"(?i)\b(user|agent|client)\s+(prefers|likes|dislikes|loves|hates)\s+(.+)", 1, 2, 3),
            (r"(?i)\b(user|agent|client)\s+(works\s+at|works\s+for|employed\s+by)\s+(.+)", 1, "WORKS_FOR", 3),
            (r"(?i)\b(user|agent|client)\s+(lives\s+in|resides\s+in|based\s+in)\s+(.+)", 1, "LIVES_IN", 3),
            (r"(?i)\b(user|agent|client)\s+(using|uses|switched\s+to)\s+(.+)", 1, "USES", 3),
            (r"(?i)\b(.+?)\s+is\s+(?:a|an)\s+(.+)", 1, "IS_A", 2),
        ]

        for sentence in text.split("."):
            s = sentence.strip()
            if not s:
                continue
            for pat, s_idx, p_val, o_idx in patterns:
                match = re.search(pat, s)
                if match:
                    subj = match.group(s_idx).strip().title()
                    pred = p_val if isinstance(p_val, str) else match.group(p_val).strip().upper().replace(" ", "_")
                    obj = match.group(o_idx).strip().title()
                    if len(subj) > 1 and len(obj) > 1:
                        triples.append((subj, pred, obj))
                        break

        return triples
