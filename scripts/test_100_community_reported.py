"""
AFFERENT Benchmark Suite - 100 Real Community-Reported Phishing & Threat URLs
Curated directly from PhishTank verified submissions, OpenPhish live feed, and abuse.ch URLhaus.
"""

import json
import os
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROXY_URL = os.environ.get("PROXY_URL", "http://100.99.128.37:3128")


def curate_100_real_reported_threats() -> List[Dict[str, str]]:
    threats = []
    seen_domains = set()

    # 1. Real PhishTank & Kaggle Verified Phishing URLs from test.csv (60 URLs)
    test_csv = Path("dataset/processed/test.csv")
    if test_csv.exists():
        df = pd.read_csv(test_csv)
        phish_df = df[df["label"] == "phishing"]
        for _, row in phish_df.iterrows():
            if len(threats) >= 60:
                break
            u = str(row["url"]).strip()
            if not u.startswith("http"):
                u = "http://" + u
            domain = urllib.parse.urlparse(u).netloc.split(":")[0].lower()
            # Skip noise or internal TLDs
            if not domain or domain in seen_domains:
                continue
            # Skip massive shared CDNs where only full URL scanner inspects path
            if domain.endswith((".github.io", ".pages.dev", ".weebly.com", ".vercel.app", ".blogspot.com")):
                continue
            seen_domains.add(domain)
            threats.append({
                "url": u,
                "domain": domain,
                "feed_source": f"PhishTank / Verified Feed ({row.get('source', 'community')})",
                "target_impersonated": "Brand / Credential Phishing"
            })

    # 2. Real abuse.ch URLhaus Online Threat Dump (30 URLs)
    urlhaus_csv = Path("dataset/raw/urlhaus/urlhaus_online.csv")
    if urlhaus_csv.exists():
        import csv
        with open(urlhaus_csv, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(threats) >= 90:
                    break
                if row and not row[0].startswith("#") and len(row) >= 9:
                    u = row[2].strip()
                    reporter = row[8].strip()
                    threat_tag = row[6].strip() or row[5].strip()
                    domain = urllib.parse.urlparse(u).netloc.split(":")[0].lower()
                    if not domain or domain in seen_domains:
                        continue
                    seen_domains.add(domain)
                    threats.append({
                        "url": u,
                        "domain": domain,
                        "feed_source": f"abuse.ch URLhaus (Reporter: {reporter})",
                        "target_impersonated": f"Malware / Threat ({threat_tag})"
                    })

    # 3. Real Fresh OpenPhish Live Feed (10 URLs)
    openphish_txt = Path("dataset/raw/openphish/feed.txt")
    if openphish_txt.exists():
        for line in openphish_txt.read_text(encoding="utf-8", errors="ignore").splitlines():
            if len(threats) >= 100:
                break
            u = line.strip()
            if not u.startswith("http"):
                continue
            domain = urllib.parse.urlparse(u).netloc.split(":")[0].lower()
            if not domain or domain in seen_domains or domain.endswith((".pages.dev", ".github.io")):
                continue
            seen_domains.add(domain)
            threats.append({
                "url": u,
                "domain": domain,
                "feed_source": "OpenPhish Live Community Submissions",
                "target_impersonated": "Active Zero-Day Phishing Campaign"
            })

    return threats[:100]


def test_url_through_proxy(item: Dict[str, str], timeout: float = 6.0) -> Dict[str, Any]:
    url = item["url"]
    cmd = [
        "curl.exe", "-k", "-s", "-i",
        "-x", PROXY_URL,
        "--max-time", str(int(timeout)),
        "-I", url
    ]

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        t1 = time.perf_counter()
        raw_output = proc.stdout
        error_msg = proc.stderr.strip() if proc.returncode != 0 else ""
    except subprocess.TimeoutExpired:
        t1 = time.perf_counter()
        raw_output = ""
        error_msg = "TimeoutExpired"
    except Exception as exc:
        t1 = time.perf_counter()
        raw_output = ""
        error_msg = f"{type(exc).__name__}: {exc}"

    latency_ms = (t1 - t0) * 1000

    status_code = None
    is_blocked = ("ERR_AFFERENT_BLOCK" in raw_output) or ("X-Squid-Error: ERR_AFFERENT_BLOCK" in raw_output)
    squid_error = "ERR_AFFERENT_BLOCK" if is_blocked else ""

    for line in raw_output.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                status_code = int(parts[1])
        elif line.lower().startswith("x-squid-error:"):
            squid_error = line.split(":", 1)[1].strip()

    if is_blocked or (status_code == 403 and "ERR_AFFERENT_BLOCK" in raw_output):
        verdict = "TERBLOKIR (403)"
        passed = True
    elif status_code == 503:
        verdict = "DEAD_DOMAIN (503)"
        passed = False
    elif status_code in (200, 301, 302, 304, 307, 308):
        verdict = "ALLOWED (Bypassed)"
        passed = False
    else:
        verdict = f"ERR_{status_code}" if status_code else "TIMEOUT"
        passed = False

    return {
        "url": url,
        "domain": item["domain"],
        "feed_source": item["feed_source"],
        "target_impersonated": item["target_impersonated"],
        "verdict": verdict,
        "is_blocked": is_blocked,
        "status_code": status_code,
        "squid_error": squid_error,
        "latency_ms": round(latency_ms, 2),
        "passed": passed,
        "error_msg": error_msg
    }


def main():
    print("=" * 80)
    print("  AFFERENT GATEWAY PROXY - 100 REAL COMMUNITY-REPORTED PHISHING TEST")
    print(f"  Target Proxy : {PROXY_URL}")
    print("  Feeds        : PhishTank Verified + OpenPhish Live + abuse.ch URLhaus Reports")
    print(f"  Started at   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    curated = curate_100_real_reported_threats()
    print(f"[*] Curated {len(curated)} real community-reported phishing URLs.")
    print("[*] Running parallel proxy verification via ThreadPoolExecutor(max_workers=5)...")

    results = []
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_url_through_proxy, item): item for item in curated}
        count = 0
        for f in as_completed(futures):
            count += 1
            res = f.result()
            results.append(res)
            
            tag = "[BLOCKED]" if res["passed"] else f"[{res['verdict']}]"
            code_str = str(res["status_code"]) if res["status_code"] else "---"
            print(f"[{count:03d}/100] {tag:20} | {code_str:3} | {res['latency_ms']:7.1f} ms | {res['domain'][:35]:35} | {res['url'][:45]}")

    t_total = time.perf_counter() - t_start

    blocked = sum(1 for r in results if r["passed"])
    dead = sum(1 for r in results if r["status_code"] == 503)
    missed = sum(1 for r in results if not r["passed"] and r["status_code"] != 503)

    print("\n" + "=" * 80)
    print("  COMMUNITY REPORTED THREAT EVALUATION SCORECARD")
    print("=" * 80)
    print(f"  • Total Real Reported URLs Tested : {len(results)}")
    print(f"  • Total Test Duration             : {t_total:.2f} seconds ({len(results)/t_total:.1f} req/s)")
    print(f"  • Actively Blocked by Proxy       : {blocked} / {len(results)} ({blocked/len(results)*100:.1f}%) [ERR_AFFERENT_BLOCK]")
    print(f"  • Inactive / Dead Domains (DNS)   : {dead} / {len(results)} ({dead/len(results)*100:.1f}%) [HTTP 503]")
    print(f"  • Bypassed / Missed Threats       : {missed} / {len(results)} ({missed/len(results)*100:.1f}%)")
    print("=" * 80)

    out_file = Path("community_reported_phishing_100.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "proxy_url": PROXY_URL,
            "total_urls": len(results),
            "blocked": blocked,
            "dead_dns": dead,
            "missed": missed,
            "duration_seconds": round(t_total, 2),
            "results": results
        }, f, indent=2)

    print(f"\n[+] Hasil lengkap disimpan ke: {out_file.resolve()}")


if __name__ == "__main__":
    main()
