import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
  "host": os.getenv("MYSQL_HOST", "localhost"),
  "user": os.getenv("MYSQL_USER", "root"),
  "password": os.getenv("MYSQL_PASSWORD", "root"),
  "database": os.getenv("MYSQL_DB", "github_data"),
  "port": int(os.getenv("MYSQL_PORT", 3306)),
}

def get_connection():
  return pymysql.connect(**DB_CONFIG)