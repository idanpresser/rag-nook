import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from config import config

class LMStudioSettings(BaseModel):
    temperature_segment: float = Field(default=0.2, ge=0.0, le=1.0)
    temperature_webpage: float = Field(default=0.2, ge=0.0, le=1.0)
    temperature_search: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, gt=0)
    prompt_etl: str = Field(
        default=(
            "You are a structured database enrichment assistant.\n"
            "Your sole job is to analyze conversational inputs and return a valid JSON object.\n"
            "Do NOT include any introduction, markdown wrapping (such as ```json ... ```), explanation, or trailing text.\n"
            "Return raw, valid JSON only."
        )
    )
    prompt_search: str = Field(
        default=(
            "You are a helpful research assistant utilizing a localized retrieval-augmented knowledge base. "
            "Your job is to answer user queries objectively and factually using only the provided sources. "
            "You must cite your sources explicitly in the text using bracketed numbers, e.g. [1], [2], corresponding to the source indexes."
        )
    )
    routing_etl_model: str = Field(default_factory=lambda: config.llm_model_name)
    routing_search_model: str = Field(default_factory=lambda: config.llm_model_name)

class LMStudioSettingsService:
    def __init__(self, filepath: Path = None):
        if filepath is None:
            self.filepath = config.output_dir / "lms_settings.json"
        else:
            self.filepath = filepath
        self._cached_settings = None

    def load_settings(self) -> LMStudioSettings:
        if self._cached_settings is not None:
            return self._cached_settings

        if not self.filepath.exists():
            # Create default settings
            defaults = LMStudioSettings()
            self.save_settings(defaults)
            self._cached_settings = defaults
            return defaults

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support partial loads and default fallbacks
            settings = LMStudioSettings(**data)
            self._cached_settings = settings
            return settings
        except Exception as e:
            print(f"[LMStudio Settings] Error loading settings, falling back to defaults: {str(e)}")
            defaults = LMStudioSettings()
            self._cached_settings = defaults
            return defaults

    def save_settings(self, settings: LMStudioSettings) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(settings.model_dump_json(indent=2))
        self._cached_settings = settings

settings_service = LMStudioSettingsService()
