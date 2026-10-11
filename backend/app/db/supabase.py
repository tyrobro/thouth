from supabase import create_client, Client
from app.core.config import get_settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_supabase_client() -> Client:
    client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )
    return client


def verify_supabase_connection() -> bool:
    try:
        client = get_supabase_client()
        # Use rpc ping instead of table query
        client.rpc("pg_sleep", {"seconds": 0}).execute()
        logger.info("Supabase connection verified")
        return True
    except Exception as e:
        # If we get a Postgres error it means we're connected, just the function doesn't exist
        error_str = str(e)
        if "PGRST" in error_str or "postgres" in error_str.lower() or "pg_sleep" in error_str.lower():
            logger.info("Supabase connection verified via error response")
            return True
        logger.error(f"Supabase connection failed: {e}")
        return False
