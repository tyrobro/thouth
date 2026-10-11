from neo4j import GraphDatabase, Driver
from app.core.config import get_settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_driver() -> Driver:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    return driver


def verify_neo4j_connection() -> bool:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        logger.info("Neo4j connection verified")
        return True
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        return False


def close_driver():
    driver = get_driver()
    driver.close()