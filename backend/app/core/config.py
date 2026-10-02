from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Thouth"
    app_env: str = "development"
    secret_key: str

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # Weaviate
    weaviate_url: str
    weaviate_api_key: str

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_reasoning_model: str = "llama3.1:8b"
    ollama_fast_model: str = "mistral:7b"
    ollama_embed_model: str = "nomic-embed-text"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cloudflare
    tunnel_url: str = ""

    class Config:
        env_file = "backend/.env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
