# scrapers/whois_enricher.py
import whois          # pip install python-whois
import pandas as pd
from datetime import datetime

def enrich_with_whois(domains: list):
    records = []
    for domain in domains:
        try:
            w = whois.whois(domain)
            created = w.creation_date
            if isinstance(created, list):
                created = created[0]
            records.append({
                "domain": domain,
                "registrar": w.registrar,
                "creation_date": str(created) if created else None,
                "country": w.country,
                "domain_age_days": (datetime.utcnow() - created).days if created else None
            })
        except Exception:
            records.append({
                "domain": domain,
                "registrar": None,
                "creation_date": None,
                "country": None,
                "domain_age_days": None
            })

    return pd.DataFrame(records)