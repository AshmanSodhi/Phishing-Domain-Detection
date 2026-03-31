# scrapers/ctlogs.py
import requests
import pandas as pd
import time
import logging
from datetime import datetime

log = logging.getLogger(__name__)

# ── crt.sh works reliably with actual domain queries, not keyword wildcards ──
# Format: %.brand.com  →  all subdomains of brand.com
# This catches typosquatting like paypal-secure.com, amazon-login.net etc.

BRAND_DOMAINS = [
    # major brands that phishers impersonate most
    "paypal.com",
    "amazon.com",
    "apple.com",
    "microsoft.com",
    "google.com",
    "netflix.com",
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "dropbox.com",
    "twitter.com",
]

# ── separately, query known suspicious TLDs directly ─────────────────────────
SUSPICIOUS_TLDS = [
    "%.tk",
    "%.ml",
    "%.ga",
    "%.cf",
    "%.gq",
    "%.xyz",
    "%.top",
    "%.click",
]

DELAY_BETWEEN_QUERIES = 3.0
MAX_RETRIES           = 3
BACKOFF_FACTOR        = 2.0


def _query_crtsh(query: str, retries: int = 0) -> list:
    """
    Query crt.sh for a single domain or pattern.
    Uses the Identity parameter which is still fully supported.
    """
    url    = "https://crt.sh/"
    params = {"q": query, "output": "json"}

    try:
        resp = requests.get(url, params=params, timeout=30,
                            headers={"Accept": "application/json"})

        if resp.status_code == 429:
            wait = DELAY_BETWEEN_QUERIES * (BACKOFF_FACTOR ** retries)
            log.warning(f"  Rate limited on '{query}'. Waiting {wait:.1f}s...")
            time.sleep(wait)
            if retries < MAX_RETRIES:
                return _query_crtsh(query, retries + 1)
            return []

        if resp.status_code != 200:
            log.warning(f"  HTTP {resp.status_code} for '{query}'")
            return []

        # crt.sh returns empty string sometimes for overloaded queries
        if not resp.text.strip():
            log.warning(f"  Empty response for '{query}' — skipping")
            return []

        return resp.json()

    except requests.exceptions.Timeout:
        log.warning(f"  Timeout on '{query}'")
        if retries < MAX_RETRIES:
            time.sleep(DELAY_BETWEEN_QUERIES * (BACKOFF_FACTOR ** retries))
            return _query_crtsh(query, retries + 1)
        return []

    except Exception as e:
        log.error(f"  Error on '{query}': {e}")
        return []


def _parse_entries(entries: list, source_query: str) -> list:
    """Extract clean domain names from crt.sh cert entries."""
    records = []
    for entry in entries:
        raw_names = entry.get("name_value", "")
        issued_at = entry.get("entry_timestamp", "")

        for name in raw_names.split("\n"):
            domain = name.strip().lstrip("*.").lower()

            # skip wildcards, empty, and single-label entries
            if not domain or "." not in domain or "*" in domain:
                continue

            records.append({
                "url":            "http://" + domain,
                "domain":         domain,
                "label":          -1,           # unknown — resolved in Phase 2
                "source":         "ct_logs",
                "ct_query":       source_query,
                "cert_issued_at": issued_at,
                "scraped_at":     datetime.utcnow().isoformat(),
            })
    return records


def fetch_ct_logs(brand_domains: list = BRAND_DOMAINS,
                  include_suspicious_tlds: bool = False,
                  delay: float = DELAY_BETWEEN_QUERIES) -> pd.DataFrame:
    """
    Scrape crt.sh using brand domain queries.
    Each query finds all certs issued for subdomains of that brand —
    catching typosquats like paypal-login.com, apple-id-verify.net etc.
    """
    all_records = []
    queries     = ["%."+d for d in brand_domains]

    if include_suspicious_tlds:
        queries += SUSPICIOUS_TLDS

    total = len(queries)

    for i, query in enumerate(queries, 1):
        log.info(f"[CT logs] ({i}/{total}) Querying: '{query}'")
        entries = _query_crtsh(query)

        if not entries:
            log.info(f"  No results for '{query}'")
        else:
            batch = _parse_entries(entries, query)
            all_records.extend(batch)
            log.info(f"  {len(entries)} certs → {len(batch)} domains")

        if i < total:
            time.sleep(delay)

    if not all_records:
        log.warning("[CT logs] No records collected at all.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    before = len(df)
    df = df.drop_duplicates(subset=["domain"])
    log.info(f"[CT logs] {before:,} raw → {len(df):,} unique domains")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    df = fetch_ct_logs()
    print(df.head(10))
    print(f"\nTotal: {len(df):,} domains")