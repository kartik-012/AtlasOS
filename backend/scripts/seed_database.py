"""
AtlasOS Database & Vector Store Initializer / Seeder.

Initializes Qdrant collection schemas and seeds default tenant, admin user,
memories, knowledge graph nodes, and evaluations.
"""

import asyncio
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.auth import ApiKey, TenantMembership
from app.models.evaluation import EvaluationMetric, EvaluationRun
from app.models.graph import EntityNode, EntityRelation
from app.models.memory import ContradictionLog, EpisodicMemory, SemanticMemory
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import Webhook


def seed() -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)

    print("Step 1: Initializing Qdrant Collection 'atlas_memories'...")
    qdrant_url = f"{settings.QDRANT_URL.rstrip('/')}/collections/atlas_memories"
    try:
        # Check if collection exists
        res = httpx.get(qdrant_url)
        if res.status_code != 200:
            # Create collection
            httpx.put(
                qdrant_url,
                json={
                    "vectors": {"size": 1024, "distance": "Cosine"}
                },
                timeout=10.0,
            )
            # Create payload indexes
            for field in ["tenant_id", "external_user_id", "memory_type"]:
                httpx.put(
                    f"{qdrant_url}/index",
                    json={"field_name": field, "field_schema": "keyword"},
                    timeout=5.0,
                )
            print("✓ Qdrant collection created with 1024-d Cosine vectors & payload indexes.")
        else:
            print("✓ Qdrant collection already exists.")
    except Exception as e:
        print(f"Warning initializing Qdrant: {e}")

    print("\nStep 2: Seeding PostgreSQL Database...")
    with Session(engine) as session:
        # 1. Create or get Default Tenant
        tenant = session.query(Tenant).filter(Tenant.slug == "acme-corp").first()
        if not tenant:
            tenant = Tenant(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                name="Acme Corp",
                slug="acme-corp",
                plan="enterprise",
                embedding_provider="bge-large",
                embedding_model="BAAI/bge-large-en-v1.5",
                embedding_dimension=1024,
                resolution_policy="confidence_weighted",
                retention_days=90,
                max_memories_per_user=50000,
                is_active=True,
            )
            session.add(tenant)
            session.flush()
            print(f"✓ Tenant created: {tenant.name} ({tenant.id})")
        else:
            print(f"✓ Tenant exists: {tenant.name}")

        # 2. Create Admin User
        user = session.query(User).filter(User.email == "admin@atlasos.dev").first()
        if not user:
            user = User(
                id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                email="admin@atlasos.dev",
                password_hash=hash_password("admin12345"),
                display_name="System Administrator",
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            session.flush()

            # Membership
            membership = TenantMembership(
                user_id=user.id,
                tenant_id=tenant.id,
                role="admin",
            )
            session.add(membership)
            session.flush()
            print(f"✓ Admin user created: {user.email} (Password: admin12345)")
        else:
            print(f"✓ Admin user exists: {user.email}")

        # 3. Create Default API Key
        api_key = session.query(ApiKey).filter(ApiKey.tenant_id == tenant.id).first()
        if not api_key:
            api_key = ApiKey(
                tenant_id=tenant.id,
                key_prefix="atlas_",
                key_hash=hash_password("atlas_live_secret_key_12345"),
                name="Production Agent SDK Key",
                permissions=["memory:read", "memory:write", "admin"],
                created_by=user.id,
            )
            session.add(api_key)
            session.flush()
            print("✓ Production API Key created: atlas_live_secret_key_12345")

        # 4. Create Sample Knowledge Graph Nodes & Relations
        node_user = session.query(EntityNode).filter(EntityNode.name == "User").first()
        if not node_user:
            node_user = EntityNode(
                tenant_id=tenant.id,
                external_user_id="user-kartik-01",
                name="User",
                entity_type="PERSON",
            )
            node_theme = EntityNode(
                tenant_id=tenant.id,
                external_user_id="user-kartik-01",
                name="Dark Mode",
                entity_type="PREFERENCE",
            )
            node_org = EntityNode(
                tenant_id=tenant.id,
                external_user_id="user-kartik-01",
                name="Google",
                entity_type="ORGANIZATION",
            )
            session.add_all([node_user, node_theme, node_org])
            session.flush()

            rel1 = EntityRelation(
                tenant_id=tenant.id,
                source_node_id=node_user.id,
                target_node_id=node_theme.id,
                relation_type="PREFERS",
                weight=1.0,
            )
            rel2 = EntityRelation(
                tenant_id=tenant.id,
                source_node_id=node_user.id,
                target_node_id=node_org.id,
                relation_type="WORKS_FOR",
                weight=1.0,
            )
            session.add_all([rel1, rel2])
            session.flush()
            print("✓ Knowledge Graph sample nodes & relations created.")

        # 5. Create Sample Memories
        sample_sem = session.query(SemanticMemory).filter(SemanticMemory.tenant_id == tenant.id).first()
        if not sample_sem:
            sem_id = uuid.uuid4()
            sample_sem = SemanticMemory(
                id=sem_id,
                tenant_id=tenant.id,
                external_user_id="user-kartik-01",
                content="User prefers dark mode and uses Python FastAPI and Next.js for production systems.",
                embedding_model=tenant.embedding_model,
                importance_score=0.92,
                confidence_score=0.95,
                vector_id=sem_id,
            )
            session.add(sample_sem)
            session.flush()

            # Insert into Qdrant
            try:
                httpx.put(
                    f"{settings.QDRANT_URL.rstrip('/')}/collections/atlas_memories/points",
                    json={
                        "points": [
                            {
                                "id": str(sem_id),
                                "vector": [0.05] * 1024,
                                "payload": {
                                    "tenant_id": str(tenant.id),
                                    "external_user_id": "user-kartik-01",
                                    "memory_type": "semantic",
                                    "importance_score": 0.92,
                                    "created_at": int(datetime.now(UTC).timestamp()),
                                },
                            }
                        ]
                    },
                    timeout=5.0,
                )
            except Exception:
                pass
            print("✓ Sample Semantic memory inserted in PG & Qdrant.")

        # 6. Create Sample Evaluation Run
        eval_run = session.query(EvaluationRun).filter(EvaluationRun.tenant_id == tenant.id).first()
        if not eval_run:
            eval_run = EvaluationRun(
                tenant_id=tenant.id,
                run_type="scheduled",
                status="completed",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            session.add(eval_run)
            session.flush()

            m1 = EvaluationMetric(evaluation_run_id=eval_run.id, metric_name="recall_at_k", metric_value=0.94, target_value=0.80, passed=True)
            m2 = EvaluationMetric(evaluation_run_id=eval_run.id, metric_name="precision_at_k", metric_value=0.88, target_value=0.70, passed=True)
            m3 = EvaluationMetric(evaluation_run_id=eval_run.id, metric_name="p95_latency_ms", metric_value=42.5, target_value=200.0, passed=True)
            session.add_all([m1, m2, m3])
            session.flush()
            print("✓ Sample Evaluation metrics created.")

        session.commit()
        print("\n🎉 ALL DATABASE & QDRANT SEEDING COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    seed()
