import os
from pathlib import Path

from dotenv import load_dotenv


# Locate the project root from this package
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment variables from the project's .env file
load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FREECRYPTO_TOKEN = os.getenv("FREECRYPTO_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# Validate the required configuration
required_keys = {
    "GROQ_API_KEY": GROQ_API_KEY,
    "FREECRYPTO_TOKEN": FREECRYPTO_TOKEN,
    "NEWSAPI_KEY": NEWSAPI_KEY,
}

for name, value in required_keys.items():
    if not value:
        raise ValueError(f"Missing API key: {name}")