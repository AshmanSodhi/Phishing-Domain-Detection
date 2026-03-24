# scrapers/ctlogs.py
import requests
import pandas as pd
import time
import logging
from datetime import datetime

log = logging.getLogger(__name__)

BRAND_KEYWORDS = [
    "paypal", "amazon", "apple", "microsoft", "netflix",
    "instagram", "facebook", "login", "secure", "banking",
]

# ── rate limiting config ───────────────────────────────────────────────────
DELAY_BETWEEN_QUERIES = 2.0    # seconds between each crt.sh query
MAX_RETRIES           = 3      # retry a failed query this many times
BACKOFF_FACTOR        = 2.0    # multiply delay by this on each retry


def _query_crtsh(keyword: str, retries: int = 0) -> list:
    """
    Query crt.sh for one keyword. Returns raw list of cert entries.
    Handles rate limiting with exponential backoff.
    """
    url = f"https://crt.sh/?q=%25{keyword}%25&output=json"
    try:
        resp = requests.get(url, timeout=30,
                            headers={"Accept": "application/json"})

        if resp.status_code == 429:
            wait = DELAY_BETWEEN_QUERIES * (BACKOFF_FACTOR ** retries)
            log.warning(f"  Rate limited on '{keyword}'. "
                        f"Waiting {wait:.1f}s before retry...")
            time.sleep(wait)
            if retries < MAX_RETRIES:
                return _query_crtsh(keyword, retries + 1)
            else:
                log.error(f"  Giving up on '{keyword}' after {MAX_RETRIES} retries")
                return []

        if resp.status_code != 200:
            log.warning(f"  HTTP {resp.status_code} for '{keyword}'")
            return []

        return resp.json()

    except requests.exceptions.Timeout:
        log.warning(f"  Timeout on '{keyword}'")
        if retries < MAX_RETRIES:
            time.sleep(DELAY_BETWEEN_QUERIES * (BACKOFF_FACTOR ** retries))
            return _query_crtsh(keyword, retries + 1)
        return []

    except Exception as e:
        log.error(f"  Unexpected error on '{keyword}': {e}")
        return []


def fetch_ct_logs(keywords: list = BRAND_KEYWORDS,
                  delay: float = DELAY_BETWEEN_QUERIES) -> pd.DataFrame:
    """
    Scrape crt.sh for all keywords with rate limiting.
    Returns a deduplicated DataFrame of newly seen domains.
    """
    all_records = []
    total       = len(keywords)

    for i, keyword in enumerate(keywords, 1):
        log.info(f"[CT logs] ({i}/{total}) Querying: '{keyword}'")
        entries = _query_crtsh(keyword)

        for entry in entries:
            raw_names = entry.get("name_value", "")
            for name in raw_names.split("\n"):
                domain = name.strip().lstrip("*.").lower()
                if domain and "." in domain:
                    all_records.append({
                        "url":            "http://" + domain,
                        "domain":         domain,
                        "label":          -1,
                        "source":         "ct_logs",
                        "ct_keyword":     keyword,
                        "cert_issued_at": entry.get("entry_timestamp"),
                        "scraped_at":     datetime.utcnow().isoformat(),
                    })

        log.info(f"  Got {len(entries)} certs so far total")

        # ── polite delay between queries ───────────────────────────────────
        # Skip delay after the last keyword
        if i < total:
            log.info(f"  Waiting {delay}s before next query...")
            time.sleep(delay)

    df = pd.DataFrame(all_records)
    if df.empty:
        return df

    before = len(df)
    df = df.drop_duplicates(subset=["domain"])
    log.info(f"[CT logs] {before:,} raw → {len(df):,} unique domains")
    return df