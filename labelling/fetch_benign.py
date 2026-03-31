# labelling/fetch_benign.py
import requests, zipfile, io, pandas as pd, sqlite3, os
from datetime import datetime

def fetch_tranco(top_n: int = 25000):
    print("[Tranco] Downloading top-1M list...")
    url  = "https://tranco-list.eu/top-1m.csv.zip"
    resp = requests.get(url, timeout=60)

    z = zipfile.ZipFile(io.BytesIO(resp.content))
    with z.open("top-1m.csv") as f:
        df = pd.read_csv(f, header=None, names=["rank", "domain"])

    df = df.head(top_n).copy()
    df["url"]        = "http://" + df["domain"]
    df["label"]      = 0
    df["source"]     = "tranco"
    df["verified"]   = 1
    df["scraped_at"] = datetime.utcnow().isoformat()

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/phishing.db")

    # only insert domains not already in the table
    existing = pd.read_sql("SELECT domain FROM domains", conn)
    existing_set = set(existing["domain"].tolist())
    df = df[~df["domain"].isin(existing_set)]

    df[["url", "domain", "label", "source", "verified", "scraped_at"]].to_sql(
        "domains", conn, if_exists="append", index=False
    )
    conn.close()
    print(f"[Tranco] Inserted {len(df):,} legit domains (label=0)")

if __name__ == "__main__":
    fetch_tranco()