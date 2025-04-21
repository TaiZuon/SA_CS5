import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKENS = os.getenv("GITHUB_TOKENS", "").split(",")
GITHUB_API_URL = "https://api.github.com"
GITSTAR_RANKING_URL = "https://gitstar-ranking.com"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "github_data"),
    "port": int(os.getenv("DB_PORT", 3307))
}

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s"
}

# config.py
SAVE_MODE = "db" 
#SAVE_MODE = "sql" 
SQL_DUMP_PATH = os.path.join(os.getcwd(), "output")


