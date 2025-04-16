import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKENS = os.getenv("GITHUB_TOKENS", "").split(",")
GITHUB_API_URL = "https://api.github.com"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "github_data")
}

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s"
}
