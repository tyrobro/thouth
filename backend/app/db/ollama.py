from langchain_ollama import ChatOllama, OllamaEmbeddings
from app.core.config import get_settings
from functools import lru_cache
import httpx
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_reasoning_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_reasoning_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )


@lru_cache()
def get_fast_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_fast_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )


@lru_cache()
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def verify_ollama_connection() -> bool:
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags")
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            logger.info(f"Ollama connected. Models available: {models}")
            return True
        return False
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return False