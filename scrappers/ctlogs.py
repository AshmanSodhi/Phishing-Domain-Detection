# scrapers/ctlogs.py
import requests
import pandas as pd
from datetime import datetime
import time

BRAND_KEYWORDS = [
    "paypal", "amazon", "google", "apple", "microsoft",
    "netflix", "instagram", "facebook", "login", "secure",
    "account", "banking", "verify", "update"
]

def fetch_ct_logs(keywords=BRAND_KEYWORDS):
    records = []
    for keyword in keywords:
        url = f"https://crt.sh/?q=%25{keyword}%25&output=json"
        print(f"[CT logs] Querying: {keyword}")
        try:
            resp = requests.get(url, timeout=30)
            entries = resp.json()
            for entry in entries:
                name = entry.get("name_value", "")
                for domain in name.split("\n"):
                    domain = domain.strip().lstrip("*.")
                    if domain:
                        records.append({
                            "url": "http://" + domain,
                            "domain": domain,
                            "label": -1,          # unknown — will be labelled in Phase 2
                            "source": "ct_logs",
                            "cert_issued_at": entry.get("entry_timestamp"),
                            "scraped_at": datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"  Error on '{keyword}': {e}")
        time.sleep(1)  # be polite to crt.sh

    df = pd.DataFrame(records).drop_duplicates(subset=["domain"])
    print(f"[CT logs] Collected {len(df)} unique domains")
    return df