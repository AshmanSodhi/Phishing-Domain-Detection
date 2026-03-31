# features/pipeline.py
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from lexical      import extract_lexical
from rdap_ssl     import extract_rdap_ssl
from html_features import extract_html

def _extract_row(row: dict) -> dict:
    url    = str(row["url"])
    domain = str(row["domain"])
    feats  = {
        "url":    url,
        "domain": domain,
        "label":  row["label"],
    }
    # lexical — always works
    feats.update(extract_lexical(url))

    # rdap + ssl — network, may fail gracefully
    feats.update(extract_rdap_ssl(domain))

    # html — network, may fail gracefully
    feats.update(extract_html(url))

    return feats


def build_feature_matrix(
    csv_path:    str = "data/labelled_domains.csv",
    out_path:    str = "data/feature_matrix.csv",
    max_workers: int = 1000,
    limit:       int = None
):
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)

    rows = df.to_dict("records")
    print(f"Extracting features for {len(rows):,} domains "
          f"with {max_workers} workers...")

    results  = []
    errors   = 0
    total    = len(rows)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_extract_row, row): i
            for i, row in enumerate(rows)
        }
        for i, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as e:
                errors += 1

            if i % 1000 == 0 or i == total:
                print(f"  {i:,}/{total:,} "
                      f"({i/total*100:.1f}%) | errors: {errors}")

    out = pd.DataFrame(results)
    os.makedirs("data", exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nFeature matrix saved → {out_path}")
    print(f"Shape: {out.shape}")
    return out


if __name__ == "__main__":
    # start with limit=500 to test, then remove limit for full run
    build_feature_matrix()