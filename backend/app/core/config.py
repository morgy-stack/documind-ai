from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    demo_mode: bool = False
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    chroma_persist_directory: str = "./storage/chroma"
    upload_dir: str = "./storage/uploads"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    max_file_size_mb: int = 15
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def use_demo(self) -> bool:
        """Demo mode runs fully offline: on request, or automatically when no API key is set."""
        return self.demo_mode or not self.openai_api_key

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def prepare_directories(self) -> None:
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.prepare_directories()
    return settings


settings = get_settings()
