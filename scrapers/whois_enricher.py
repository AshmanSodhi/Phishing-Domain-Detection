# scrapers/whois_enricher.py
import httpx
import pandas as pd
import sqlite3
import os
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

MAX_WORKERS = 50
BATCH_SIZE  = 500
RDAP_URL    = "https://rdap.org/domain/"

def _query_single(domain: str) -> dict:
    base = {
        "domain":             domain,
        "registrar":          None,
        "creation_date":      None,
        "country":            None,
        "domain_age_days":    None,
        "privacy_protected":  0,
        "whois_error":        None,
        "fetched_at":         datetime.utcnow().isoformat(),
    }
    try:
        resp = httpx.get(
            RDAP_URL + domain,
            timeout=6,                        # hard 6s timeout — no hanging
            follow_redirects=True
        )

        if resp.status_code != 200:
            base["whois_error"] = f"http_{resp.status_code}"
            return base

        data = resp.json()

        # ── registrar ─────────────────────────────────────────────────────
        for entity in data.get("entities", []):
            roles = entity.get("roles", [])
            if "registrar" in roles:
                vcard = entity.get("vcardArray", [])
                if vcard and len(vcard) > 1:
                    for field in vcard[1]:
                        if field[0] == "fn":
                            base["registrar"] = str(field[3])[:80]

        # ── dates ─────────────────────────────────────────────────────────
        for event in data.get("events", []):
            if event.get("eventAction") == "registration":
                date_str = event.get("eventDate", "")[:10]
                try:
                    created = datetime.strptime(date_str, "%Y-%m-%d")
                    base["creation_date"]   = date_str
                    base["domain_age_days"] = (datetime.utcnow() - created).days
                except Exception:
                    pass

        # ── country ───────────────────────────────────────────────────────
        for entity in data.get("entities", []):
            addr = entity.get("vcardArray", [])
            if addr and len(addr) > 1:
                for field in addr[1]:
                    if field[0] == "adr":
                        country = field[1].get("cc", "")
                        if country:
                            base["country"] = country.upper()

        # ── privacy protected ─────────────────────────────────────────────
        registrar = str(base.get("registrar") or "").lower()
        base["privacy_protected"] = int(any(k in registrar for k in
                                       ["privacy","proxy","protect","guard"]))

    except httpx.TimeoutException:
        base["whois_error"] = "timeout"

    except Exception as e:
        base["whois_error"] = str(e)[:120]

    return base


def enrich_with_whois_parallel(domains: list,
                                db_path: str = "data/phishing.db") -> pd.DataFrame:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # ── load cache ────────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
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
    try:
        cached       = pd.read_sql("SELECT domain FROM whois_cache", conn)
        already_done = set(cached["domain"].tolist())
    except Exception:
        already_done = set()
    conn.close()

    todo = [d for d in domains if d not in already_done]
    log.info(f"Total: {len(domains):,} | Cached: {len(already_done):,} | To fetch: {len(todo):,}")

    if not todo:
        log.info("All domains already cached.")
        return _load_cache(db_path)

    results = []
    errors  = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_query_single, d): d for d in todo}

        for i, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as e:
                errors += 1

            if i % 500 == 0:
                pct = (i / len(todo)) * 100
                log.info(f"  {i:,}/{len(todo):,} ({pct:.1f}%) | errors: {errors}")

            if len(results) >= BATCH_SIZE:
                _save_batch(results, db_path)
                results = []

    if results:
        _save_batch(results, db_path)

    log.info(f"RDAP done. Total errors: {errors}")
    return _load_cache(db_path)


def _save_batch(rows: list, db_path: str):
    df   = pd.DataFrame(rows)
    conn = sqlite3.connect(db_path)
    df.to_sql("whois_cache", conn, if_exists="append",
              index=False, method="multi")
    conn.execute("""
        DELETE FROM whois_cache WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM whois_cache GROUP BY domain
        )
    """)
    conn.commit()
    conn.close()
    log.info(f"  Saved batch of {len(rows)}")


def _load_cache(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df   = pd.read_sql("SELECT * FROM whois_cache", conn)
    conn.close()
    return df