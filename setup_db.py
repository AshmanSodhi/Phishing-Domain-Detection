# setup_db.py
import sqlite3
import os

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect("data/phishing.db")
cursor = conn.cursor()

cursor.executescript("""
    CREATE TABLE IF NOT EXISTS domains (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        url             TEXT NOT NULL,
        domain          TEXT NOT NULL,
        label           INTEGER DEFAULT -1,  -- 1=phishing, 0=legit, -1=unknown
        source          TEXT,
        verified        INTEGER DEFAULT 0,
        registrar       TEXT,
        creation_date   TEXT,
        country         TEXT,
        domain_age_days INTEGER,
        cert_issued_at  TEXT,
        scraped_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS whois_cache (
        domain          TEXT PRIMARY KEY,
        registrar       TEXT,
        creation_date   TEXT,
        country         TEXT,
        domain_age_days INTEGER,
        fetched_at      TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_domain ON domains(domain);
    CREATE INDEX IF NOT EXISTS idx_label  ON domains(label);
    CREATE INDEX IF NOT EXISTS idx_source ON domains(source);
""")

conn.commit()
conn.close()
print("Database created at data/phishing.db")