# fix_db.py
import sqlite3

conn = sqlite3.connect("data/phishing.db")
conn.execute("DROP TABLE IF EXISTS whois_cache")
conn.commit()
conn.close()
print("Done — whois_cache dropped. Run collect.py now.")