# labelling/resolve_unknown.py
import sqlite3, pandas as pd, requests
import re, math
from collections import Counter
from datetime import datetime

BLACKLISTS = [
    "https://urlhaus.abuse.ch/downloads/text/",
    "https://openphish.com/feed.txt",
]

BRANDS = [
    "paypal","amazon","google","apple","microsoft",
    "netflix","instagram","facebook","chase","wellsfargo",
    "bankofamerica","linkedin","dropbox","twitter"
]

RISKY_TLDS = {
    "tk","ml","ga","cf","gq","xyz","top","club",
    "online","site","fun","pw","cc","click"
}


def _load_blacklist() -> set:
    bad = set()
    for url in BLACKLISTS:
        try:
            resp = requests.get(url, timeout=20)
            for line in resp.text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    domain = line.replace("https://","") \
                                 .replace("http://","") \
                                 .split("/")[0].lower()
                    bad.add(domain)
        except Exception as e:
            print(f"  Blacklist error: {e}")
    print(f"[Blacklist] {len(bad):,} known-bad domains loaded")
    return bad


def _load_tranco() -> set:
    print("[Tranco] Loading for resolution...")
    url  = "https://tranco-list.eu/top-1m.csv.zip"
    import zipfile, io
    resp = requests.get(url, timeout=60)
    z    = zipfile.ZipFile(io.BytesIO(resp.content))
    with z.open("top-1m.csv") as f:
        df = pd.read_csv(f, header=None, names=["rank","domain"])
    s = set(df["domain"].str.lower().tolist())
    print(f"[Tranco] {len(s):,} legit domains loaded")
    return s


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    l = len(s)
    return -sum((c/l)*math.log2(c/l) for c in counts.values())


def _suspicion_score(domain: str) -> int:
    score = 0
    tld = domain.split(".")[-1].lower()
    sld = domain.split(".")[-2].lower() if len(domain.split(".")) > 1 else domain

    # brand name in domain but not the real brand domain
    if any(b in domain and sld != b for b in BRANDS):
        score += 2
    if tld in RISKY_TLDS:
        score += 1
    if domain.count("-") >= 2:
        score += 1
    if len(domain) > 40:
        score += 1
    if re.search(r"\d{4,}", domain):
        score += 1
    if _entropy(domain) > 3.8:
        score += 1

    return score


def resolve_unknown_labels():
    conn = sqlite3.connect("data/phishing.db")
    df = pd.read_sql(
    "SELECT rowid as id, domain FROM domains WHERE label = -1", conn
    )
    conn.close()
    print(f"\n[Resolve] {len(df):,} unknown domains to resolve")

    if df.empty:
        print("No unknown domains found.")
        return

    blacklist = _load_blacklist()
    tranco    = _load_tranco()

    labels    = []
    decisions = []

    for _, row in df.iterrows():
        d = row["domain"].lower()

        if d in blacklist:
            labels.append(1)
            decisions.append("blacklist_hit")

        elif d in tranco:
            labels.append(0)
            decisions.append("tranco_legit")

        else:
            score = _suspicion_score(d)
            if score >= 3:
                labels.append(1)
                decisions.append(f"heuristic_phish")
            else:
                labels.append(-1)
                decisions.append("still_unknown")

    df["new_label"] = labels
    df["decision"]  = decisions

    # summary
    print("\nResolution breakdown:")
    print(df["decision"].value_counts().to_string())

    # update DB — only rows that got resolved
    resolved = df[df["new_label"] != -1]
    conn     = sqlite3.connect("data/phishing.db")
    cursor   = conn.cursor()
    for _, row in resolved.iterrows():
        cursor.execute(
            "UPDATE domains SET label = ? WHERE rowid = ?",
            (int(row["new_label"]), int(row["id"]))
        )
    conn.commit()
    conn.close()

    still_unknown = (df["new_label"] == -1).sum()
    print(f"\nResolved: {len(resolved):,} | Still unknown: {still_unknown:,}")
    print("(still_unknown rows are excluded from training — that's fine)")

if __name__ == "__main__":
    resolve_unknown_labels()