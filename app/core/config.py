from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    APP_TITLE: str = "DOD SBIR/STTR Scraper"
    APP_DESCRIPTION: str = "API for searching and downloading DOD SBIR/STTR topics"
    APP_VERSION: str = "1.0.0"
    
    # CORS settings
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # DOD API settings
    DOD_API_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    DOD_API_REFERER: str = "https://www.dodsbirsttr.mil/"
    DOD_SEARCH_API_URL: str = "https://www.dodsbirsttr.mil/api/topics/search"
    DOD_PDF_API_TEMPLATE: str = "https://www.dodsbirsttr.mil/api/topics/{topic_uid}/pdf"

    # For loading .env file if present
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()