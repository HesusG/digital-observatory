from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # LLM providers (Ollama first, then cloud fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Obsidian
    obsidian_vault_path: Path = Path("/mnt/d/DM01")

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_receiver: str = ""

    # Google Sheets
    google_sheet_id: str = ""
    google_credentials_path: Path = Path("credentials.json")

    # Paths
    user_profile_path: Path = Path("config/profiles/user_profile.txt")
    wordpress_config_path: Path = Path("config/sources/wordpress_sites.yaml")
    state_db_path: Path = Path("data/state.db")

    # App
    log_level: str = "INFO"
    app_port: int = 8400

    # Processing
    dedup_distance_threshold: float = 0.15
    embedding_model: str = "all-MiniLM-L6-v2"
    high_affinity_threshold: int = 8
    weekly_email_interval_days: int = 7

    # AI-article (marketing) pipeline
    ai_article_min_relevance: int = 6   # drafts only written above this
    ai_supported_langs: list[str] = ["es", "en"]
    ai_default_platforms: list[str] = ["x", "linkedin", "bluesky"]

    # Wake-on-LAN sidecar (see deploy/wol-service/). The observatory hits this
    # service when Ollama is unreachable, then polls until Ollama responds.
    wol_service_url: str = "http://host.docker.internal:9999"
    wol_wait_max_seconds: int = 30
    wol_poll_interval_seconds: float = 2.0

    # Postiz publisher (see deploy/postiz/). Slice 1 only wires Bluesky.
    postiz_base_url: str = "http://100.84.156.15:5000"
    postiz_api_key: str = ""
    postiz_bluesky_integration_id: str = ""

    # WordPress scraping
    wp_default_keywords: list[str] = [
        "artificial intelligence",
        "data science",
        "education technology",
        "scholarship PhD",
        "fellowship AI",
        "remote AI jobs",
    ]
    wp_max_results_per_site: int = 10
    wp_request_delay_min: float = 1.0
    wp_request_delay_max: float = 2.5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
