import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Skylark Drones Monday BI Agent"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Monday.com API Configuration
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
    DEALS_BOARD_ID: str = os.getenv("DEALS_BOARD_ID", "")
    WORK_ORDERS_BOARD_ID: str = os.getenv("WORK_ORDERS_BOARD_ID", "")
    
    # In-memory Cache TTL (in seconds)
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "120"))
    
    # LLM Settings (Groq / OpenAI compatible)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # Data directory fallback
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
