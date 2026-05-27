import os
import re
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from local .env file if it exists
load_dotenv()


class AppConfig(BaseModel):
    # Core Directories
    workspace_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve())
    output_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output")
    scraped_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output" / "scraped_pages")
    vector_db_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output" / "vector_db")

    # WhatsApp Input
    chat_file_path: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "chat.txt")

    # Time-Based Turn Chunking Configuration
    # Max gap between messages in the same segment (7200s = 2 hours)
    max_segment_gap_seconds: int = Field(default_factory=lambda: int(os.getenv("MAX_SEGMENT_GAP_SECONDS", 7200)))

    # Scraper Settings & Magic Numbers
    request_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", 15)))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_RETRIES", 3)))
    backoff_factor: float = Field(default_factory=lambda: float(os.getenv("BACKOFF_FACTOR", 2.0)))
    max_scraper_workers: int = Field(default_factory=lambda: int(os.getenv("MAX_SCRAPER_WORKERS", 4)))
    user_agent: str = Field(default_factory=lambda: os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ))

    # API Agnostic LLM Server Settings (Standard OpenAI or local LM Studio / Ollama compatible endpoints)
    llm_base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"))
    llm_api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", "lm-studio"))
    llm_model_name: str = Field(default_factory=lambda: os.getenv("LLM_MODEL_NAME", "google/gemma-4-e2b"))
    
    # LM Studio Python SDK settings
    lms_sdk_enabled: bool = Field(default_factory=lambda: os.getenv("LMS_SDK_ENABLED", "True").lower() in ("true", "1", "yes"))
    lms_model_key: str = Field(default_factory=lambda: os.getenv("LMS_MODEL_KEY", os.getenv("LLM_MODEL_NAME", "google/gemma-4-e2b")))
    
    # LLM Inference Magic Numbers
    llm_timeout: float = Field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", 180.0)))
    llm_temperature_segment: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE_SEGMENT", 0.2)))
    llm_temperature_webpage: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE_WEBPAGE", 0.2)))
    llm_temperature_search: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE_SEARCH", 0.3)))
    llm_max_retries: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", 3)))
    llm_retry_backoff_factor: float = Field(default_factory=lambda: float(os.getenv("LLM_RETRY_BACKOFF_FACTOR", 1.5)))
    max_web_text_length: int = Field(default_factory=lambda: int(os.getenv("MAX_WEB_TEXT_LENGTH", 8000)))

    # Regex Compilation (for performant repeated matching)
    whatsapp_header_regex: re.Pattern = re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*-\s*(.*)$"
    )
    sender_message_regex: re.Pattern = re.compile(
        r"^([^:]+):\s*(.*)$"
    )
    url_regex: re.Pattern = re.compile(
        r"https?://[^\s]+"
    )
    attachment_regex: re.Pattern = re.compile(
        r"([^\(:\n]+\.\w+)\s*\(file attached\)"
    )
    media_omitted_regex: re.Pattern = re.compile(
        r"^<Media omitted>$"
    )

    # Backward Compatibility Aliases for LM Studio naming
    @property
    def lm_studio_base_url(self) -> str:
        return self.llm_base_url

    @property
    def lm_studio_api_key(self) -> str:
        return self.llm_api_key

    def initialize_directories(self):
        """Creates output, scraper, and vector directories if they do not exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.scraped_dir, exist_ok=True)
        os.makedirs(self.vector_db_dir, exist_ok=True)

# Instantiate a single clean configuration instance
config = AppConfig()
