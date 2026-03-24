# collect.py
import sqlite3
import pandas as pd
from scrapers.phishtank import fetch_phishtank
from scrapers.openphish import fetch_openphish
from scrapers.ctlogs import fetch_ct_logs
from scrapers.whois_enricher import enrich_with_whois

def run_collection():
    # --- scrape all sources ---
    df_pt  = fetch_phishtank()
    df_op  = fetch_openphish()
    df_ct  = fetch_ct_logs()

    # --- combine ---
    df = pd.concat([df_pt, df_op, df_ct], ignore_index=True)
    df = df.drop_duplicates(subset=["domain"])
    print(f"\nTotal unique domains: {len(df)}")

    # --- enrich with WHOIS ---
    print("\nEnriching with WHOIS (slow — ~1s per domain)...")
    whois_df = enrich_with_whois(df["domain"].tolist())
    df = df.merge(whois_df, on="domain", how="left")

    # --- save to SQLite ---
    conn = sqlite3.connect("data/phishing.db")
    df.to_sql("domains", conn, if_exists="replace", index=False)
    conn.close()

    # --- also save CSV ---
    df.to_csv("data/raw_domains.csv", index=False)
    print(f"\nSaved {len(df)} rows to data/phishing.db and data/raw_domains.csv")
    return df

if __name__ == "__main__":
    run_collection()
