# labelling/balance_check.py
import sqlite3, pandas as pd

def check_balance():
    conn = sqlite3.connect("data/phishing.db")
    df   = pd.read_sql("""
        SELECT label, COUNT(*) as count
        FROM domains
        GROUP BY label
        ORDER BY label
    """, conn)
    conn.close()

    print("\n=== Dataset balance ===")
    label_map = {1: "phishing", 0: "legit", -1: "unknown"}
    for _, row in df.iterrows():
        name = label_map.get(int(row["label"]), "?")
        print(f"  label={int(row['label'])} ({name}): {int(row['count']):,}")

    legit_count   = df[df["label"]==0]["count"].values
    phish_count   = df[df["label"]==1]["count"].values

    if len(legit_count) == 0 or len(phish_count) == 0:
        print("\nWARNING: Missing one class entirely.")
        return

    legit_count = int(legit_count[0])
    phish_count = int(phish_count[0])
    ratio       = phish_count / legit_count

    print(f"\n  Phishing : Legit ratio = {ratio:.2f}:1")

    if ratio > 3:
        print("  WARNING: Imbalanced. SMOTE will be applied during training.")
    elif ratio < 0.5:
        print("  WARNING: Too many legit domains. Consider trimming Tranco.")
    else:
        print("  Balance looks good. No SMOTE needed.")

if __name__ == "__main__":
    check_balance()