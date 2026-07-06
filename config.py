import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "tripmind-dev")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
    )
    USE_LLM_NOTIFICATIONS = os.getenv("USE_LLM_NOTIFICATIONS", "false").lower() == "true"
    MOCK_DATA_DIR = BASE_DIR / "mock_data"
    LOG_FILE = BASE_DIR / "logs" / "agent.log"