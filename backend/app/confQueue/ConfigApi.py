import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_KEY: str = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
    VIRUSTOTAL_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")

settings = Settings()