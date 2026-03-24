# scrapers/phishtank.py
import requests
import json
import pandas as pd
from datetime import datetime

PHISHTANK_API_KEY = "your_api_key_here"

def fetch_phishtank():
    url = "http://data.phishtank.com/data/{}/online-valid.json".format(PHISHTANK_API_KEY)
    print("[PhishTank] Fetching...")
    response = requests.get(url, headers={"User-Agent": "phishing-detector/1.0"})
    data = response.json()

    records = []
    for entry in data:
        records.append({
            "url": entry["url"],
            "domain": entry["url"].split("/")[2] if "/" in entry["url"] else entry["url"],
            "label": 1,
            "source": "phishtank",
            "verified": entry["verified"] == "yes",
            "scraped_at": datetime.utcnow().isoformat()
        })

    df = pd.DataFrame(records)
    print(f"[PhishTank] Collected {len(df)} URLs")
    return df