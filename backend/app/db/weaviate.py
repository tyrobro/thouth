import weaviate
from weaviate.auth import Auth
from app.core.config import get_settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_weaviate_client() -> weaviate.WeaviateClient:
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.weaviate_url,
        auth_credentials=Auth.api_key(settings.weaviate_api_key),
    )
    return client


def verify_weaviate_connection() -> bool:
    try:
        client = get_weaviate_client()
        if client.is_ready():
            logger.info("Weaviate connection verified")
            return True
        return False
    except Exception as e:
        logger.error(f"Weaviate connection failed: {e}")
        return False