import asyncio
import os
import sys

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

# Add the backend directory to sys.path so we can import our application modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings


async def init_qdrant() -> None:
    """
    Initialize the Qdrant vector database collection.

    This script creates the `atlas_memories` collection if it doesn't exist,
    or updates it if it does. It configures the vector size based on the
    EMBEDDING_DIMENSION setting and sets up payload indices for efficient
    filtering (tenant_id, memory_type, superseded).
    """
    settings = get_settings()
    
    print(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
    client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    
    collection_name = "atlas_memories"
    
    try:
        # Check if collection exists
        collections_response = await client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        
        if collection_name in collection_names:
            print(f"Collection '{collection_name}' already exists.")
        else:
            print(f"Creating collection '{collection_name}' with vector size {settings.EMBEDDING_DIMENSION}...")
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE,
                ),
            )
            print("Collection created successfully.")
            
        # Create payload indices for fast filtering
        print("Ensuring payload indices exist...")
        
        # tenant_id index is critical for multi-tenant isolation
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="tenant_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        # memory_type index (episodic or semantic)
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="memory_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        # superseded index (boolean) to quickly filter out outdated memories
        await client.create_payload_index(
            collection_name=collection_name,
            field_name="superseded",
            field_schema=models.PayloadSchemaType.BOOL,
        )
        
        print("Qdrant initialization complete.")
        
    except Exception as e:
        print(f"Error initializing Qdrant: {e}")
        sys.exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(init_qdrant())
