import time
import json
import socket
import re
import urllib.parse
import urllib.request

# Endpoint API dari llama-server.exe lokal
SERVER_URL = "http://localhost:8080/v1/chat/completions"

# Pola Leksikon Risiko & Domain Terpercaya
JUDOL_PATTERNS = re.compile(r"(slot|gacor|maxwin|olympus|zeus|pragmatic|rtp|jackpot|judol)", re.IGNORECASE)
PHISHING_PATTERNS = re.compile(r"(login|verify|account|update|secure|bank|paypal|klikbca)", re.IGNORECASE)
PORN_PATTERNS = re.compile(r"(porn|sex|xxx|adult|bokep|toket|hentai|xvideos)", re.IGNORECASE)

HIGH_RISK_TLDS = {".site", ".xyz", ".top", ".online", ".tech", ".vip", ".cc", ".icu", ".pw", ".click"}
INSTITUTIONAL_TLDS = {".go.id", ".ac.id", ".co.id", ".mil.id", ".net.id"}
POPULAR_DOMAINS = {
    "netflix.com", "google.com", "microsoft.com", "facebook.com", 
    "youtube.com", "github.com", "instagram.com", "wikipedia.org", "bca.co.id"
}


def check_domain_live(hostname, timeout=0.8):
    if not hostname:
        return False
    try:
        # Gunakan settimeout pada socket spesifik agar tidak merusak global timeout urllib
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((hostname, 80))
        s.close()
        return True
    except Exception:
        return False


def extract_quick_metadata(url_str):
    parsed = urllib.parse.urlparse(url_str if "://" in url_str else "http://" + url_str)
    hostname = parsed.hostname or ""
    scheme = parsed.scheme.lower()
    
    parts = hostname.split(".")
    tld = "." + parts[-1] if len(parts) > 1 else ""
    registered_domain = ".".join(parts[-2:]) if len(parts) >= 2 else hostname

    # Pengecekan Domain Terpercaya/Whitelisted
    is_trusted = (registered_domain in POPULAR_DOMAINS) or any(hostname.endswith(t) for t in INSTITUTIONAL_TLDS)

    lexicon_hits = []
    if JUDOL_PATTERNS.search(url_str):
        lexicon_hits.append("judol")
    if PHISHING_PATTERNS.search(url_str):
        lexicon_hits.append("phishing_keywords")
    if PORN_PATTERNS.search(url_str):
        lexicon_hits.append("adult_content")

    is_live = check_domain_live(hostname)

    return {
        "hostname": hostname,
        "registered_domain": registered_domain,
        "tld": tld,
        "has_ssl": scheme == "https",
        "lexicon_hits": lexicon_hits,
        "is_live": is_live,
        "is_trusted": is_trusted,
        "is_high_risk_tld": tld in HIGH_RISK_TLDS
    }


def query_qwen_server(user_prompt):
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Anda adalah Agent Keamanan Siber 'Human Firewall'. Analisis metadata URL dan berikan keputusan serta alasan logis dalam format JSON."
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 200,
        # Memaksa llama-server mengembalikan format JSON murni
        "response_format": {"type": "json_object"}
    }

    req = urllib.request.Request(
        SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as response:
        res_data = json.loads(response.read().decode("utf-8"))
    latency_ms = (time.perf_counter() - t0) * 1000

    raw_content = res_data["choices"][0]["message"]["content"]
    
    # Pembersih Teks Markdown (```json ... ```) jika disisipkan oleh model
    cleaned_content = raw_content.strip()
    if cleaned_content.startswith("```"):
        cleaned_content = re.sub(r"^```(?:json)?\n?", "", cleaned_content)
        cleaned_content = re.sub(r"\n?```$", "", cleaned_content)
        cleaned_content = cleaned_content.strip()

    return cleaned_content, latency_ms


def test_single_url(url: str, sim_bilstm_score: float = 0.7800):
    meta = extract_quick_metadata(url)
    
    prompt = (
        f"Analisis URL berikut:\n"
        f"- URL: {url}\n"
        f"- Registered Domain: {meta['registered_domain']}\n"
        f"- Char-BiLSTM Score: {sim_bilstm_score:.4f}\n"
        f"- TLD: {meta['tld']}\n"
        f"- Status Domain Aktif: {'Ya' if meta['is_live'] else 'Tidak / Unreachable'}\n"
        f"- Protocol HTTPS: {'Ya' if meta['has_ssl'] else 'Tidak'}\n"
        f"- Indikator Leksikon: {meta['lexicon_hits'] if meta['lexicon_hits'] else 'Tidak Ada'}\n"
        f"- Domain Populer/Terpercaya: {'Ya (Whitelisted/Institutional)' if meta['is_trusted'] else 'Tidak'}"
    )

    print("\n" + "="*70)
    print("PROMPT METADATA DIKIRIM KE MODEL:")
    print("="*70)
    print(prompt)
    print("-" * 70)

    try:
        raw_response, latency_ms = query_qwen_server(prompt)

        print("RAW OUTPUT SCANNING DARI QWEN SLM:")
        print("="*70)
        print(raw_response)
        print("="*70)
        print(f"Latensi Inference Tier-2: {latency_ms:.2f} ms")
        
        try:
            parsed_json = json.loads(raw_response)
            print("\nFORMATTED JSON VERDICT (VALID):")
            print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
        except json.JSONDecodeError as e:
            print(f"\n[WARN] Gagal parse JSON: {e}")

        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Gagal menghubungi server llama.cpp: {e}")
        print("Pastikan llama-server.exe sudah berjalan di port 8080!\n")


if __name__ == "__main__":
    print("=== TIER-2 SLM RAW SCANNING TESTER (FIXED) ===")
    while True:
        try:
            target_url = input("\nMasukkan URL baru yang ingin dites (atau 'q' untuk keluar): ").strip()
            if not target_url or target_url.lower() == 'q':
                print("Pengujian selesai.")
                break
            
            score_input = input("Masukkan skor Char-BiLSTM (default 0.7800): ").strip()
            bilstm_score = float(score_input) if score_input else 0.7800
            
            test_single_url(target_url, bilstm_score)
        except KeyboardInterrupt:
            print("\nPengujian dihentikan.")
            break
        except Exception as e:
            print(f"[ERROR] Terjadi kesalahan: {e}\n")