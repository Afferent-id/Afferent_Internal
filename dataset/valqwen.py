import time
import json
import socket
import re
import urllib.parse
import urllib.request
from pathlib import Path
import pandas as pd

# Endpoint API llama-server.exe lokal
SERVER_URL = "http://localhost:8080/v1/chat/completions"

# Path Dataset & Hasil Output
DATASET_PATH = Path(r"D:\Data Ade\Antigravity 2.0\Hackaton\Human_Firewall\dataset\processed\test.csv")
OUTPUT_RESULT_PATH = Path(r"D:\Data Ade\Antigravity 2.0\Hackaton\Human_Firewall\Finetune LLM\batch_test_results.csv")

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
        "is_trusted": is_trusted
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
    
    cleaned_content = raw_content.strip()
    if cleaned_content.startswith("```"):
        cleaned_content = re.sub(r"^```(?:json)?\n?", "", cleaned_content)
        cleaned_content = re.sub(r"\n?```$", "", cleaned_content)
        cleaned_content = cleaned_content.strip()

    return cleaned_content, latency_ms


def run_batch_evaluation(max_samples=50):
    if not DATASET_PATH.exists():
        print(f"[ERROR] File dataset tidak ditemukan di: {DATASET_PATH}")
        return

    print(f"[INFO] Membaca dataset dari {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)
    
    # Deteksi nama kolom URL
    url_col = "url" if "url" in df.columns else df.columns[0]
    total_to_eval = min(len(df), max_samples)

    print(f"\n==============================================================")
    print(f" MEMULAI BATCH TESTING QWEN SLM ({total_to_eval} SAMPEL)")
    print(f"==============================================================\n")

    latencies = []
    valid_json_count = 0
    block_count = 0
    allow_count = 0
    results = []

    for idx, row in df.head(total_to_eval).iterrows():
        url = str(row[url_col]).strip()
        score_val = float(row.get("score", row.get("bilstm_score", 0.7800)))
        
        meta = extract_quick_metadata(url)
        prompt = (
            f"Analisis URL berikut:\n"
            f"- URL: {url}\n"
            f"- Registered Domain: {meta['registered_domain']}\n"
            f"- Char-BiLSTM Score: {score_val:.4f}\n"
            f"- TLD: {meta['tld']}\n"
            f"- Status Domain Aktif: {'Ya' if meta['is_live'] else 'Tidak / Unreachable'}\n"
            f"- Protocol HTTPS: {'Ya' if meta['has_ssl'] else 'Tidak'}\n"
            f"- Indikator Leksikon: {meta['lexicon_hits'] if meta['lexicon_hits'] else 'Tidak Ada'}\n"
            f"- Domain Populer/Terpercaya: {'Ya (Whitelisted/Institutional)' if meta['is_trusted'] else 'Tidak'}"
        )

        try:
            raw_response, latency_ms = query_qwen_server(prompt)
            latencies.append(latency_ms)

            parsed = json.loads(raw_response)
            valid_json_count += 1

            verdict = parsed.get("verdict", "UNKNOWN")
            risk_score = parsed.get("risk_score", 0.0)
            reasoning = parsed.get("reasoning", "")
            category = parsed.get("category", "")

            if verdict == "BLOCK":
                block_count += 1
            elif verdict == "ALLOW":
                allow_count += 1

            print(f"[{idx+1:02d}/{total_to_eval:02d}] {url[:45]:<45} | Verdict: {verdict:<5} | Score: {risk_score:.2f} | Latency: {latency_ms:.0f} ms")

            results.append({
                "url": url,
                "input_score": score_val,
                "verdict": verdict,
                "risk_score": risk_score,
                "category": category,
                "reasoning": reasoning,
                "latency_ms": round(latency_ms, 2)
            })

        except Exception as e:
            print(f"[{idx+1:02d}/{total_to_eval:02d}] {url[:45]:<45} | ERROR: {e}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    print("\n" + "="*62)
    print(" REKAPITULASI BATCH EVALUATION TIER-2 SLM")
    print("="*62)
    print(f"Total Sampel Dites     : {len(results)}")
    print(f"JSON Format Valid      : {valid_json_count}/{len(results)} ({valid_json_count/len(results)*100:.1f}%)" if results else "0")
    print(f"Rata-rata Latensi      : {avg_latency:.2f} ms")
    print(f"Keputusan BLOCK        : {block_count}")
    print(f"Keputusan ALLOW        : {allow_count}")
    print("="*62)

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_RESULT_PATH, index=False)
    print(f"\n[SELESAI] Hasil detail telah disimpan ke:\n{OUTPUT_RESULT_PATH}\n")


if __name__ == "__main__":
    # Ubah nilai max_samples jika ingin menguji lebih dari 50 baris
    run_batch_evaluation(max_samples=50)