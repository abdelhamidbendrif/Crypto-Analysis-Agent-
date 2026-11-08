import os
import json
import sys
import requests
from dotenv import load_dotenv
from newsapi import NewsApiClient

sys.stdout = open("results.txt", "w", encoding="utf-8")
# Load .env
load_dotenv()

FREECRYPTO_TOKEN = os.getenv("FREECRYPTO_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

if not FREECRYPTO_TOKEN or not NEWSAPI_KEY:
    raise ValueError(
        "Check FREECRYPTO_TOKEN and NEWSAPI_KEY in your .env file."
    )

headers = {
    "Authorization": f"Bearer {FREECRYPTO_TOKEN}"
}


# 1. Crypto List

print("\n========== Crypto List ==========")

response = requests.get(
    "https://api.freecryptoapi.com/v1/getCryptoList",
    headers=headers,
    timeout=30,
)

print("HTTP status:", response.status_code)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))


# 2. جلب بيانات Bitcoin
print("\n========== Bitcoin Data ==========")

response = requests.get(
    "https://api.freecryptoapi.com/v1/getData",
    headers=headers,
    params={"symbol": "BTC"},
    timeout=30,
)

print("HTTP status:", response.status_code)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))


# 3.get Bitcoin News
print("\n========== Bitcoin News ==========")

newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

articles = newsapi.get_everything(
    q="bitcoin",
    language="en",
    sort_by="relevancy",
    page=1,
    page_size=5,
)

print(json.dumps(articles, indent=2, ensure_ascii=False))