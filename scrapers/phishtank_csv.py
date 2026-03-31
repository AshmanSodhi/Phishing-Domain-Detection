# scrapers/phishtank_csv.py
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

def load_phishtank_csv(path: str = "data/phishtank_raw.csv",
                       verified_only: bool = True) -> pd.DataFrame:
    """
    Load a locally downloaded PhishTank CSV and normalize it
    into the same format as every other scraper in the pipeline.
    """
    print(f"[PhishTank CSV] Loading from {path}...")
    df_raw = pd.read_csv(path, low_memory=False)

    print(f"  Raw rows: {len(df_raw):,}")
    print(f"  Columns: {df_raw.columns.tolist()}")

    # ── filter to verified phishing only ──────────────────────────────────
    if verified_only and "verified" in df_raw.columns:
        df_raw = df_raw[df_raw["verified"] == "yes"].copy()
        print(f"  After verified filter: {len(df_raw):,} rows")

    records = []
    for _, row in df_raw.iterrows():
        try:
            raw_url = str(row["url"]).strip()
            parsed  = urlparse(raw_url)
            domain  = parsed.netloc.lower()

            # strip port if present e.g. "evil.com:8080"
            domain = domain.split(":")[0]

            if not domain:
                continue

            records.append({
                "url":        raw_url,
                "domain":     domain,
                "label":      1,
                "source":     "phishtank_csv",
                "verified":   True,
                "scraped_at": datetime.utcnow().isoformat(),
            })
        except Exception:
            continue

    df = pd.DataFrame(records).drop_duplicates(subset=["domain"])
    print(f"[PhishTank CSV] {len(df):,} unique phishing domains loaded")
    return df