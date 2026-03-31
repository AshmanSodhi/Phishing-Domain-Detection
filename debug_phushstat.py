# debug_phishstats.py  — run this once to inspect the raw feed
import requests
import io
import pandas as pd

resp = requests.get("https://phishstats.info/phish_score.csv", timeout=30,
                    headers={"User-Agent": "PhishDetector/1.0"})

print("=== FIRST 20 RAW LINES ===")
lines = resp.text.splitlines()
for i, line in enumerate(lines[:20]):
    print(f"{i:02d}: {repr(line)}")

print("\n=== TRYING TO PARSE AS CSV ===")
all_lines = "\n".join(lines)
df = pd.read_csv(io.StringIO(all_lines), on_bad_lines="skip", header=None)
print("Shape:", df.shape)
print("First 5 rows:")
print(df.head())
print("\nColumn dtypes:")
print(df.dtypes)