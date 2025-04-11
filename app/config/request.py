import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
  "Accept": "application/vnd.github+json",
  "Authorization": f"token {TOKEN}"
}