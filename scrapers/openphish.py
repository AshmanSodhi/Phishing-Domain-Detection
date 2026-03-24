# scrapers/openphish.py
import requests
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime

def fetch_openphish():
    url = "https://openphish.com/feed.txt"
    print("[OpenPhish] Fetching feed...")
    response = requests.get(url, timeout=30)
    lines = [l.strip() for l in response.text.splitlines() if l.strip()]

    records = []
    for raw_url in lines:
        try:
            parsed = urlparse(raw_url)
            records.append({
                "url": raw_url,
                "domain": parsed.netloc,
                "label": 1,
                "source": "openphish",
                "verified": True,
                "scraped_at": datetime.utcnow().isoformat()
            })
        except Exception:
            continue

    df = pd.DataFrame(records)
    print(f"[OpenPhish] Collected {len(df)} URLs")
    return df