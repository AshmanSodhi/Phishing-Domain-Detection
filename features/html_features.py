# features/html_features.py
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PhishDetector/1.0)"}

def extract_html(url: str) -> dict:
    out = {
        "is_reachable":         0,
        "status_code":         -1,
        "redirect_count":      -1,
        "final_domain_diff":   -1,
        "has_login_form":      -1,
        "has_password_field":  -1,
        "iframe_count":        -1,
        "script_count":        -1,
        "meta_refresh":        -1,
        "ext_links_ratio":     -1,
        "title_mismatch":      -1,
    }
    try:
        resp = httpx.get(
            url,
            timeout=8,
            follow_redirects=True,
            headers=HEADERS,
            verify=False          # many phishing sites have bad certs
        )

        out["is_reachable"]   = 1
        out["status_code"]    = resp.status_code
        out["redirect_count"] = len(resp.history)

        orig_domain  = urlparse(url).netloc
        final_domain = urlparse(str(resp.url)).netloc
        out["final_domain_diff"] = int(orig_domain != final_domain)

        soup = BeautifulSoup(resp.text, "html.parser")

        out["has_login_form"]     = int(len(soup.find_all("form")) > 0)
        out["has_password_field"] = int(
            len(soup.find_all("input", {"type": "password"})) > 0
        )
        out["iframe_count"]  = len(soup.find_all("iframe"))
        out["script_count"]  = len(soup.find_all("script"))
        out["meta_refresh"]  = int(bool(
            soup.find("meta", attrs={"http-equiv": "refresh"})
        ))

        links = soup.find_all("a", href=True)
        if links:
            ext = sum(
                1 for a in links
                if urlparse(a["href"]).netloc not in ("", orig_domain)
            )
            out["ext_links_ratio"] = round(ext / len(links), 4)

        title = soup.find("title")
        title_text = title.text.strip().lower() if title else ""
        out["title_mismatch"] = int(
            orig_domain not in title_text and len(title_text) > 0
        )

    except Exception:
        pass

    return out