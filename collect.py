# collect.py
import sqlite3
import os
import pandas as pd
from scrapers.phishtank_csv     import load_phishtank_csv
from scrapers.openphish         import fetch_openphish
from scrapers.ctlogs            import fetch_ct_logs
from scrapers.whois_enricher    import enrich_with_whois_parallel

def run_collection():
    # ensure data/ folder and DB exist
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/phishing.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whois_cache (
            domain            TEXT PRIMARY KEY,
            registrar         TEXT,
            creation_date     TEXT,
            country           TEXT,
            domain_age_days   INTEGER,
            privacy_protected INTEGER,
            whois_error       TEXT,
            fetched_at        TEXT
        )
    """)
    conn.commit()
    conn.close()

    # ── scrape all sources ─────────────────────────────────────────────────
    df_pt = load_phishtank_csv("data/phishtank_raw.csv")   # ← changed
    df_op = fetch_openphish()
    df_ct = fetch_ct_logs()

    df = pd.concat([df_pt, df_op, df_ct], ignore_index=True)
    df = df.drop_duplicates(subset=["domain"])
    print(f"\nTotal unique domains before WHOIS: {len(df):,}")

    # ── WHOIS enrichment ───────────────────────────────────────────────────
    whois_df = enrich_with_whois_parallel(df["domain"].tolist())
    df = df.merge(whois_df, on="domain", how="left")

    # ── save ───────────────────────────────────────────────────────────────
    conn = sqlite3.connect("data/phishing.db")
    df.to_sql("domains", conn, if_exists="replace", index=False)
    conn.close()

    df.to_csv("data/raw_domains.csv", index=False)

    print(f"\nFinal dataset: {len(df):,} rows")
    print("\nBy source:")
    print(df["source"].value_counts().to_string())
    print("\nBy label:")
    print(df["label"].value_counts().to_string())

if __name__ == "__main__":
    run_collection()