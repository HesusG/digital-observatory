from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    gemini_api_key: str = ""

    obsidian_vault_path: Path = Path("/mnt/d/DM01")

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_receiver: str = ""

    log_level: str = "INFO"
    app_port: int = 8400

    dedup_distance_threshold: float = 0.15
    embedding_model: str = "all-MiniLM-L6-v2"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
