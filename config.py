import os
import re
from pathlib import Path
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    # Core Directories
    workspace_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve())
    output_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output")
    scraped_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output" / "scraped_pages")
    vector_db_dir: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "output" / "vector_db")

    # WhatsApp Input
    chat_file_path: Path = Field(default_factory=lambda: Path(__file__).parent.resolve() / "chat.txt")

    # Time-Based Turn Chunking Configuration
    # 2 Hours in seconds
    max_segment_gap_seconds: int = 7200  

    # Scraper Settings
    request_timeout_seconds: int = 15
    max_retries: int = 3
    backoff_factor: float = 2.0
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Local LLM Server (LM Studio)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_api_key: str = "lm-studio"
    llm_model_name: str = "local-model"  # Default name for LM Studio

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
        r"([\w\-]+\.\w+)\s*\(file attached\)"
    )
    media_omitted_regex: re.Pattern = re.compile(
        r"^<Media omitted>$"
    )

    def initialize_directories(self):
        """Creates output, scraper, and vector directories if they do not exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.scraped_dir, exist_ok=True)
        os.makedirs(self.vector_db_dir, exist_ok=True)

# Instantiate a single clean configuration instance
config = AppConfig()
