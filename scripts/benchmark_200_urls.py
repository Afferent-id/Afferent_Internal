"""
AFFERENT Security Gateway - 200 URL Benchmark Suite
Executes 100 Benign URLs and 100 Malicious URLs through the live Squid Gateway Proxy (100.99.128.37:3128).
Captures real-time latency, HTTP status codes, Squid error headers, and classification accuracy.
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROXY_URL = os.environ.get("PROXY_URL", "http://100.99.128.37:3128")

# ==============================================================================
# 100 BENIGN TARGETS (Real, verified, active domains)
# ==============================================================================
BENIGN_TARGETS = [
    # Global Tech, Cloud, Open Source (30)
    {"cat": "Global Tech", "url": "https://google.com"},
    {"cat": "Global Tech", "url": "https://github.com"},
    {"cat": "Global Tech", "url": "https://microsoft.com"},
    {"cat": "Global Tech", "url": "https://apple.com"},
    {"cat": "Global Tech", "url": "https://wikipedia.org"},
    {"cat": "Global Tech", "url": "https://stackoverflow.com"},
    {"cat": "Global Tech", "url": "https://cloudflare.com"},
    {"cat": "Global Tech", "url": "https://aws.amazon.com"},
    {"cat": "Global Tech", "url": "https://python.org"},
    {"cat": "Global Tech", "url": "https://mozilla.org"},
    {"cat": "Global Tech", "url": "https://registry.npmjs.org"},
    {"cat": "Global Tech", "url": "https://pypi.org"},
    {"cat": "Global Tech", "url": "https://hub.docker.com"},
    {"cat": "Global Tech", "url": "https://gitlab.com"},
    {"cat": "Global Tech", "url": "https://bitbucket.org"},
    {"cat": "Global Tech", "url": "https://medium.com"},
    {"cat": "Global Tech", "url": "https://reddit.com"},
    {"cat": "Global Tech", "url": "https://quora.com"},
    {"cat": "Global Tech", "url": "https://linkedin.com"},
    {"cat": "Global Tech", "url": "https://zoom.us"},
    {"cat": "Global Tech", "url": "https://slack.com"},
    {"cat": "Global Tech", "url": "https://notion.so"},
    {"cat": "Global Tech", "url": "https://figma.com"},
    {"cat": "Global Tech", "url": "https://canva.com"},
    {"cat": "Global Tech", "url": "https://adobe.com"},
    {"cat": "Global Tech", "url": "https://dropbox.com"},
    {"cat": "Global Tech", "url": "https://digitalocean.com"},
    {"cat": "Global Tech", "url": "https://netlify.com"},
    {"cat": "Global Tech", "url": "https://vercel.com"},
    {"cat": "Global Tech", "url": "https://cdnjs.cloudflare.com"},

    # Indonesian Government & Public Services (25)
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemkes.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemdikbud.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemenkeu.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kominfo.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://pajak.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bkn.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bappenas.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://setneg.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://dpr.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://polri.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bps.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bmkg.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://pom.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemlu.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemendag.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemenperin.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemenkumham.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bappebti.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://ojk.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://bi.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemnaker.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://esdm.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://menpan.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kemenag.go.id"},
    {"cat": "Indonesian Govt (.go.id)", "url": "https://kejaksaan.go.id"},

    # Indonesian Universities & Education (20)
    {"cat": "Indonesian Education (.ac.id)", "url": "https://ugm.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://itb.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://ui.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unair.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://undip.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://its.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://ipb.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unpad.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://uny.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://uns.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unhas.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://usu.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unsri.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unud.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://ub.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://binus.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://telkomuniversity.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://atmajaya.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://unpar.ac.id"},
    {"cat": "Indonesian Education (.ac.id)", "url": "https://trisakti.ac.id"},

    # Indonesian Verified Banking & Financial (15)
    {"cat": "Indonesian Banking", "url": "https://bca.co.id"},
    {"cat": "Indonesian Banking", "url": "https://klikbca.com"},
    {"cat": "Indonesian Banking", "url": "https://bankmandiri.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bri.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bni.co.id"},
    {"cat": "Indonesian Banking", "url": "https://cimbniaga.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bankbsi.co.id"},
    {"cat": "Indonesian Banking", "url": "https://permatabank.com"},
    {"cat": "Indonesian Banking", "url": "https://dbs.id"},
    {"cat": "Indonesian Banking", "url": "https://btn.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bankdki.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bankbjb.co.id"},
    {"cat": "Indonesian Banking", "url": "https://panin.co.id"},
    {"cat": "Indonesian Banking", "url": "https://bankmega.com"},
    {"cat": "Indonesian Banking", "url": "https://ocbcnisp.com"},

    # Indonesian Top Tech Platforms & Media (10)
    {"cat": "Indonesian Tech & Media", "url": "https://tokopedia.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://bukalapak.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://blibli.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://tiket.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://traveloka.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://detik.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://kompas.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://tempo.co"},
    {"cat": "Indonesian Tech & Media", "url": "https://antaranews.com"},
    {"cat": "Indonesian Tech & Media", "url": "https://cnnindonesia.com"}
]

# ==============================================================================
# 100 MALICIOUS TARGETS (Judol, Typosquatting, Phishing, Malware)
# ==============================================================================
MALICIOUS_TARGETS = [
    # 1. Indonesian Online Gambling / Judol (40)
    {"cat": "Online Gambling (Judol)", "url": "http://slot88-gacor-maxwin.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot88.xyz/login"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot88.top/daftar"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot88.site/rtp"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot88.live/promo"},
    {"cat": "Online Gambling (Judol)", "url": "http://zeus-olympus-maxwin.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://pragmatic-play-gacor.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://rajawalislot88.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://judibola88-resmi.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://agen-togel-singapura.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://daftar-sbobet88-login.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://rtp-live-jarwo.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://kakekzeus-gacor88.club"},
    {"cat": "Online Gambling (Judol)", "url": "http://mahjong-ways2-maxwin.top"},
    {"cat": "Online Gambling (Judol)", "url": "http://gatotkaca77-gacor.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://link-alternatif-slot777.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://bocoran-slot-malam-ini.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://bandar-taruhan-bola-parlay.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://casino-online-indonesia88.live"},
    {"cat": "Online Gambling (Judol)", "url": "http://situs-judi-deposit-pulsa.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://depo-dana-slot-gacor.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot-gacor-hari-ini-gampang-menang.top"},
    {"cat": "Online Gambling (Judol)", "url": "http://rtp-tertinggi-hari-ini.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://poker-online-uang-asli88.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://domino-qiuqiu-terpercaya.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://bandarq-online-bonus-harian.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://rajapoker99-daftar-akun.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://link-login-slot-sensasional.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://pasti-maxwin-olympus88.top"},
    {"cat": "Online Gambling (Judol)", "url": "http://jackpot-terbesar-sweet-bonanza.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://agen-resmi-pragmatic88.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://login-member-slot88-vip.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://daftar-akun-pro-kamboja.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://server-thailand-gacor88.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://akun-pro-rusia-maxwin.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://slot-dana-tanpa-potongan88.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://link-gacor-resmi-anti-rungkad.xyz"},
    {"cat": "Online Gambling (Judol)", "url": "http://bocoran-pola-starlight-princess.site"},
    {"cat": "Online Gambling (Judol)", "url": "http://spin-gratis-bonus-new-member.online"},
    {"cat": "Online Gambling (Judol)", "url": "http://togel-hongkong-singapore-sidney88.top"},

    # 2. Banking Typosquatting & Indonesian FinTech Social Engineering (30)
    {"cat": "Banking Typosquatting", "url": "http://klikbca-login-verifikasi.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://bca-klik-update-data.site"},
    {"cat": "Banking Typosquatting", "url": "http://mybca-verifikasi-keamanan.online"},
    {"cat": "Banking Typosquatting", "url": "http://klik-bca-individual-login.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://bca-mobile-aktivasi-baru.site"},
    {"cat": "Banking Typosquatting", "url": "http://livin-mandiri-update-tarif.online"},
    {"cat": "Banking Typosquatting", "url": "http://bankmandiri-perubahan-tarif-transaksi.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://mandiri-livin-poin-hadiah.site"},
    {"cat": "Banking Typosquatting", "url": "http://livin-poin-kupon-gebyar.online"},
    {"cat": "Banking Typosquatting", "url": "http://brimo-perubahan-tarif-baru.site"},
    {"cat": "Banking Typosquatting", "url": "http://bri-mo-surat-edaran-tarif.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://ib-bri-login-perbankan.site"},
    {"cat": "Banking Typosquatting", "url": "http://undian-simpedes-bri-terbaru.online"},
    {"cat": "Banking Typosquatting", "url": "http://bni-mobile-aktivasi-rekening.online"},
    {"cat": "Banking Typosquatting", "url": "http://bni-poin-plus-tukar-hadiah.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://cimb-clicks-verifikasi-otp.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://octomobile-pembaruan-keamanan.site"},
    {"cat": "Banking Typosquatting", "url": "http://bsi-mobile-perubahan-biaya.online"},
    {"cat": "Banking Typosquatting", "url": "http://dana-kaget-saldo-gratis.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://dana-id-klaim-saldo-kaget.site"},
    {"cat": "Banking Typosquatting", "url": "http://dana-protection-verifikasi-akun.online"},
    {"cat": "Banking Typosquatting", "url": "http://gopay-klaim-voucher-cashback.site"},
    {"cat": "Banking Typosquatting", "url": "http://gopay-plus-verifikasi-ktp.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://ovo-poin-penukaran-voucher.site"},
    {"cat": "Banking Typosquatting", "url": "http://shopeepay-undian-berhadiah-mobil.online"},
    {"cat": "Banking Typosquatting", "url": "http://linkaja-pemulihan-akun-terblokir.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://pinjaman-online-ojk-cair-cepat.site"},
    {"cat": "Banking Typosquatting", "url": "http://kredivo-pembatalan-transaksi-bodong.online"},
    {"cat": "Banking Typosquatting", "url": "http://akulaku-limit-pinjaman-instan.xyz"},
    {"cat": "Banking Typosquatting", "url": "http://spaylater-penghapusan-denda.site"},

    # 3. Enterprise Account Hijacking & Phishing (20)
    {"cat": "Credential Phishing", "url": "http://phishing-verify-login-security.xyz"},
    {"cat": "Credential Phishing", "url": "http://office365-password-reset-notice.site"},
    {"cat": "Credential Phishing", "url": "http://microsoft-online-session-expired.xyz"},
    {"cat": "Credential Phishing", "url": "http://outlook-web-app-mailbox-update.online"},
    {"cat": "Credential Phishing", "url": "http://sharepoint-secure-document-portal.site"},
    {"cat": "Credential Phishing", "url": "http://google-drive-shared-document-verify.xyz"},
    {"cat": "Credential Phishing", "url": "http://google-workspace-admin-alert.site"},
    {"cat": "Credential Phishing", "url": "http://gmail-security-alert-unrecognized-device.online"},
    {"cat": "Credential Phishing", "url": "http://apple-id-verify-account-locked.online"},
    {"cat": "Credential Phishing", "url": "http://icloud-find-my-iphone-tracking.site"},
    {"cat": "Credential Phishing", "url": "http://paypal-security-center-update.xyz"},
    {"cat": "Credential Phishing", "url": "http://paypal-resolution-center-case.site"},
    {"cat": "Credential Phishing", "url": "http://dhl-express-package-delivery-failed.online"},
    {"cat": "Credential Phishing", "url": "http://fedex-tracking-customs-fee-payment.xyz"},
    {"cat": "Credential Phishing", "url": "http://netflix-billing-update-membership.site"},
    {"cat": "Credential Phishing", "url": "http://spotify-premium-payment-declined.online"},
    {"cat": "Credential Phishing", "url": "http://adobe-creative-cloud-subscription-renew.xyz"},
    {"cat": "Credential Phishing", "url": "http://dropbox-shared-invoice-pdf-download.site"},
    {"cat": "Credential Phishing", "url": "http://zoom-meeting-invitation-relogin.online"},
    {"cat": "Credential Phishing", "url": "http://webmail-corporate-ssl-upgrade.xyz"},

    # 4. Malware Droppers & Suspicious Infrastructure (10)
    {"cat": "Malware & Suspicious", "url": "http://download-crack-windows11-activator.xyz"},
    {"cat": "Malware & Suspicious", "url": "http://keygen-patch-adobe-premiere.site"},
    {"cat": "Malware & Suspicious", "url": "http://free-crypto-miner-bot-installer.online"},
    {"cat": "Malware & Suspicious", "url": "http://telegram-token-stealer-setup.xyz"},
    {"cat": "Malware & Suspicious", "url": "http://cheat-freefire-autoheadshot-apk.site"},
    {"cat": "Malware & Suspicious", "url": "http://mod-whatsapp-anti-banned-latest.online"},
    {"cat": "Malware & Suspicious", "url": "http://roblox-free-robux-generator-tool.xyz"},
    {"cat": "Malware & Suspicious", "url": "http://steam-wallet-code-hack-generator.site"},
    {"cat": "Malware & Suspicious", "url": "http://update-flash-player-plugin-install.online"},
    {"cat": "Malware & Suspicious", "url": "http://ransomware-decryption-tool-unlocker.xyz"}
]


def test_single_url(target: Dict[str, Any], timeout: float = 6.0) -> Dict[str, Any]:
    url = target["url"]
    expected_action = target["expected_action"]
    category = target["cat"]

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
        actual_action = "BLOCK"
    elif status_code is not None and not is_blocked:
        actual_action = "ALLOW"
    elif status_code == 403:
        # Origin 403 (e.g. BCA WAF blocking curl) but not Squid block
        actual_action = "ALLOW"
    else:
        actual_action = "ERROR" if error_msg else f"HTTP_{status_code}"

    # Efficacy verdict
    if expected_action == "ALLOW":
        passed = (actual_action == "ALLOW") and not is_blocked
    elif expected_action == "BLOCK":
        passed = is_blocked or (actual_action == "BLOCK")
    else:
        passed = False

    return {
        "url": url,
        "category": category,
        "expected": expected_action,
        "actual": actual_action,
        "status_code": status_code,
        "is_blocked": is_blocked,
        "squid_error": squid_error,
        "latency_ms": round(latency_ms, 2),
        "passed": passed,
        "error_msg": error_msg
    }


def main():
    print("=" * 80)
    print("  AFFERENT GATEWAY PROXY - 200 URL VERIFICATION BENCHMARK SUITE")
    print(f"  Target Proxy : {PROXY_URL}")
    print(f"  Targets      : 100 Benign URLs (ALLOW) + 100 Malicious URLs (BLOCK)")
    print(f"  Started at   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    # Prepare complete queue of 200 items
    work_items = []
    for item in BENIGN_TARGETS:
        work_items.append({**item, "expected_action": "ALLOW"})
    for item in MALICIOUS_TARGETS:
        work_items.append({**item, "expected_action": "BLOCK"})

    print(f"[*] Total items to test: {len(work_items)} ({len(BENIGN_TARGETS)} Benign + {len(MALICIOUS_TARGETS)} Malicious)")
    print("[*] Running concurrent evaluations with ThreadPoolExecutor(max_workers=6)...")

    results = []
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_item = {executor.submit(test_single_url, item): item for item in work_items}
        count = 0
        for future in as_completed(future_to_item):
            count += 1
            res = future.result()
            results.append(res)
            
            status_tag = "[PASS]" if res["passed"] else "[FAIL]"
            code_str = str(res["status_code"]) if res["status_code"] else "---"
            block_tag = " [BLOCK PAGE]" if res["is_blocked"] else ""
            print(f"[{count:03d}/200] {status_tag} | {res['category'][:22]:22} | Exp: {res['expected']:5} | Act: {res['actual']:5} | {code_str:3} | {res['latency_ms']:7.1f} ms | {res['url'][:45]}{block_tag}")

    t_total = time.perf_counter() - t_start

    # Categorize and aggregate
    benign_results = [r for r in results if r["expected"] == "ALLOW"]
    malicious_results = [r for r in results if r["expected"] == "BLOCK"]

    benign_passed = sum(1 for r in benign_results if r["passed"])
    malicious_passed = sum(1 for r in malicious_results if r["passed"])
    total_passed = benign_passed + malicious_passed

    benign_latencies = [r["latency_ms"] for r in benign_results if r["latency_ms"] > 0]
    malicious_latencies = [r["latency_ms"] for r in malicious_results if r["latency_ms"] > 0]

    mean_benign_lat = sum(benign_latencies) / len(benign_latencies) if benign_latencies else 0
    mean_malicious_lat = sum(malicious_latencies) / len(malicious_latencies) if malicious_latencies else 0

    print("\n" + "=" * 80)
    print("  EXECUTIVE ACCURACY & PERFORMANCE SCORECARD (200 URLS)")
    print("=" * 80)
    print(f"  • Total URLs Evaluated    : 200")
    print(f"  • Total Test Duration     : {t_total:.2f} seconds ({len(work_items)/t_total:.1f} req/s)")
    print(f"  • Overall Passed          : {total_passed} / 200 ({total_passed/200*100:.2f}%)")
    print("-" * 80)
    print(f"  [BENIGN TRAFFIC (100 URLs)]")
    print(f"    - Allowed (True Negative) : {benign_passed} / 100 ({benign_passed:.1f}%)")
    print(f"    - False Positive (FPR)    : {100 - benign_passed} / 100 ({(100-benign_passed):.1f}%)")
    print(f"    - Mean Latency            : {mean_benign_lat:.1f} ms (Min: {min(benign_latencies):.1f} ms | Max: {max(benign_latencies):.1f} ms)")
    print("-" * 80)
    print(f"  [MALICIOUS TRAFFIC (100 URLs)]")
    print(f"    - Blocked (True Positive) : {malicious_passed} / 100 ({malicious_passed:.1f}%)")
    print(f"    - False Negative (Missed) : {100 - malicious_passed} / 100 ({(100-malicious_passed):.1f}%)")
    print(f"    - Mean Block Latency      : {mean_malicious_lat:.1f} ms (Min: {min(malicious_latencies):.1f} ms | Max: {max(malicious_latencies):.1f} ms)")
    print("=" * 80)

    # Category breakdown table
    categories = {}
    for r in results:
        c = r["category"]
        if c not in categories:
            categories[c] = {"total": 0, "passed": 0, "latencies": []}
        categories[c]["total"] += 1
        if r["passed"]:
            categories[c]["passed"] += 1
        categories[c]["latencies"].append(r["latency_ms"])

    print("\n[+] BREAKDOWN PER KATEGORI:")
    print(f"{'Kategori':35} | {'Passed / Total':14} | {'Accuracy':8} | {'Avg Latency'}")
    print("-" * 75)
    for c, stats in sorted(categories.items()):
        acc = (stats["passed"] / stats["total"]) * 100
        avg_l = sum(stats["latencies"]) / len(stats["latencies"])
        print(f"{c:35} | {stats['passed']:3d} / {stats['total']:3d}      | {acc:6.1f}%  | {avg_l:7.1f} ms")

    # Export to JSON
    output_path = Path("benchmark_200_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "proxy_url": PROXY_URL,
            "total_urls": 200,
            "total_passed": total_passed,
            "accuracy_percent": round(total_passed / 200 * 100, 2),
            "benign_accuracy_percent": round(benign_passed / 100 * 100, 2),
            "malicious_accuracy_percent": round(malicious_passed / 100 * 100, 2),
            "duration_seconds": round(t_total, 2),
            "results": results
        }, f, indent=2)

    print(f"\n[+] Full telemetry exported to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
