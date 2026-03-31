# features/rdap_ssl.py
import httpx
import ssl
import socket
from datetime import datetime, timezone

RDAP_URL = "https://rdap.org/domain/"

def _get_rdap(domain: str) -> dict:
    out = {
        "domain_age_days":   -1,
        "days_to_expiry":    -1,
        "privacy_protected": -1,
        "rdap_error":         0,
    }
    try:
        resp = httpx.get(RDAP_URL + domain, timeout=6,
                         follow_redirects=True)
        if resp.status_code != 200:
            out["rdap_error"] = 1
            return out

        data = resp.json()

        # registration date
        for event in data.get("events", []):
            action = event.get("eventAction", "")
            date_s = event.get("eventDate", "")[:10]
            try:
                dt = datetime.strptime(date_s, "%Y-%m-%d")
                if action == "registration":
                    out["domain_age_days"] = (datetime.utcnow() - dt).days
                if action == "expiration":
                    out["days_to_expiry"]  = (dt - datetime.utcnow()).days
            except Exception:
                pass

        # privacy / proxy
        for entity in data.get("entities", []):
            vcard = entity.get("vcardArray", [])
            if vcard and len(vcard) > 1:
                for field in vcard[1]:
                    if field[0] == "fn":
                        name = str(field[3]).lower()
                        if any(k in name for k in
                               ["privacy","proxy","protect","guard"]):
                            out["privacy_protected"] = 1

    except Exception:
        out["rdap_error"] = 1

    return out


def _get_ssl(domain: str) -> dict:
    FREE_ISSUERS = {"let's encrypt", "zerossl", "buypass"}
    out = {
        "ssl_valid":    0,
        "ssl_age_days": -1,
        "is_free_ssl":  -1,
    }
    try:
        ctx  = ssl.create_default_context()
        conn = ctx.wrap_socket(
            socket.create_connection((domain, 443), timeout=5),
            server_hostname=domain
        )
        cert_bin = conn.getpeercert(binary_form=True)
        conn.close()

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        cert       = x509.load_der_x509_certificate(
                         cert_bin, default_backend())
        not_before = cert.not_valid_before_utc
        now        = datetime.now(timezone.utc)
        issuer     = cert.issuer.get_attributes_for_oid(
                         x509.NameOID.ORGANIZATION_NAME)
        issuer_str = issuer[0].value.lower() if issuer else ""

        out["ssl_valid"]    = 1
        out["ssl_age_days"] = (now - not_before).days
        out["is_free_ssl"]  = int(
            any(f in issuer_str for f in FREE_ISSUERS)
        )
    except Exception:
        pass

    return out


def extract_rdap_ssl(domain: str) -> dict:
    feats = {}
    feats.update(_get_rdap(domain))
    feats.update(_get_ssl(domain))
    return feats