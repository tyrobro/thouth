import weaviate.classes as wvc
from app.db.weaviate import get_weaviate_client
import logging

logger = logging.getLogger(__name__)

CHUNK_COLLECTION = "KnowledgeChunk"


def create_schema():
    """
    Creates the KnowledgeChunk collection in Weaviate if it doesn't exist.
    """
    client = get_weaviate_client()

    if client.collections.exists(CHUNK_COLLECTION):
        logger.info(f"Collection '{CHUNK_COLLECTION}' already exists")
        return

    client.collections.create(
        name=CHUNK_COLLECTION,
        vector_config=wvc.config.Configure.Vectors.none(),  # We supply our own vectors
        properties=[
            wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="subject", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="user_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content_type", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="chunk_index", data_type=wvc.config.DataType.INT),
            wvc.config.Property(name="concept_id", data_type=wvc.config.DataType.TEXT),
        ]
    )
    logger.info(f"Collection '{CHUNK_COLLECTION}' created successfully")
