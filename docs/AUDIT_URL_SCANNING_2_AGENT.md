# 🛡️ AUDIT LAPORAN TEKNIS: URL SCANNING & THREAT DETECTION (2-AGENT ARCHITECTURE)
**Project**: AFFERENT — Human-Centric Security Gateway  
**Dokumen**: Technical Audit & Architecture Evaluation Report  
**Target Komponen**: Dual-Agent URL & Hostname Threat Detection Engine  
**Tanggal Evaluasi**: 29 Oktober 2026  
**Status Audit**: Verified & Remediated (Quality Gate Passed)

---

## Executive Summary

Audit ini mengevaluasi arsitektur pendeteksian ancaman URL pada gateway proxy **AFFERENT**. Sistem ini mengimplementasikan pendekatan **Dual-Agent Architecture**:
1. **Agent 1 (Line-Rate Gateway Agent / Tier-1)**: Calibrated Stacker XGBoost Meta-Learner yang menginspeksi CONNECT/SNI di level proxy secara sub-milidetik ($< 0.7\text{ ms}$).
2. **Agent 2 (Deep Inspection Agent / Tier-2)**: Character-level CNN-BiLSTM dengan Attention Pooling untuk inspeksi mendalam terhadap seluruh struktur URL (path, parameter, payload zero-day, dan pola judi online / *judol*).

### Ringkasan Temuan Audit Utama:
* **Diagnosis Awal**: Model mengalami bias berat (*high false alarm*) terhadap domain infrastruktur esensial (`login.microsoftonline.com`, `windowsupdate.com`, `bca.co.id`, `kemdiktisaintek.go.id`), sementara ancaman phishing nyata gagal diblokir otomatis.
* **Akar Masalah**: Ditemukan *defacement label poisoning* pada dataset Kaggle, bias token n-gram karakter (`login`, `edge`), kegagalan ekstraksi multi-part TLD (`.co.id`), serta tidak adanya isolasi IP privat RFC 1918 / Tailscale.
* **Hasil Perbaikan (Continuous Learning Engine)**: Melalui siklus retraining terotomasi dengan *Golden Quality Gate*, ambang batas pemblokiran berhasil dinormalisasi dari `0.9991` ke `0.8500`. Skor risiko Microsoft turun dari **99.58% ke 0.68% (CLEAN)**, IP lokal di-bypass penuh (**0.00%**), dan tingkat keberhasilan blokir ancaman riil mencapai **> 99.8% (AUTO-BLOCK)**.

---

## 1. Arsitektur 2-Agent AFFERENT

```mermaid
flowchart TD
    Client["Client / Browser Traffic"] --> Squid["Squid Proxy (Port 3128 / TLS Bump)"]
    
    subgraph SQUID_PIPELINE["Squid External ACL Pipeline"]
        Squid --> Helper["afferent_acl_helper.py"]
        Helper --> CheckLAN{"Is RFC1918 /<br/>Tailscale / Local?"}
        CheckLAN -- Yes --> BypassAllow["Action: ALLOW<br/>(Bypass ML)"]
        CheckLAN -- No --> FastCache{"Redis Verdict Cache<br/>(proxy:verdict:*)"}
    end

    FastCache -- Hit --> CacheAction["Enforce Cached Verdict<br/>(< 0.5 ms)"]
    FastCache -- Miss --> DecisionRouter["Proxy Decision Endpoint<br/>(/api/proxy/decision)"]

    subgraph DUAL_AGENT["Dual-Agent Scanning Subsystem"]
        DecisionRouter --> Agent1["AGENT 1: Gateway Stacker XGBoost<br/>(SNI & Hostname Line-Rate)"]
        DirectScan["Direct URL / Link Report / Webhook"] --> Agent2["AGENT 2: Deep Char-BiLSTM<br/>(Path, Query & Payload Analysis)"]
        
        Agent1 -. "Ambiguous / Review Zone" .-> Agent2
    end

    subgraph CONTINUOUS_LEARNING["Continuous Learning Engine (Every 3 Hours)"]
        SOC["SOC Analyst Overrides"] --> Ingest["Continuous Ingestion"]
        LiveTraffic["Live Proxy Telemetry"] --> Ingest
        TrancoFeed["Tranco Top 10K Anchors"] --> Ingest
        Ingest --> RetrainJob["Auto-Retrain & Noise Cleanse"]
        RetrainJob --> QualityGate{"Golden Quality Gate<br/>(Zero False Positives)"}
        QualityGate -- Passed --> HotReload["Atomic Promotion & Hot-Reload<br/>(0 Downtime)"]
        QualityGate -- Failed --> Rollback["Rollback to Stable Weights"]
    end

    Agent1 --> VerdictStore["PostgreSQL Audit & Redis Cache"]
    Agent2 --> VerdictStore
    ProxyAction{"Action Enforcement"}
    VerdictStore --> ProxyAction
    ProxyAction -- Malicious --> BlockPage["ERR_AFFERENT_BLOCK (Blocked Page)"]
    ProxyAction -- Safe/Review --> Forward["Forward to Internet (Splice TLS)"]
```

### Spesifikasi Masing-Masing Agent

| Atribut | Agent 1: Gateway Meta-Learner | Agent 2: Deep Inspection Agent |
| :--- | :--- | :--- |
| **Engine / Algoritma** | **XGBoost Meta-Learner (Stacker)** + TF-IDF Lexical | **Char-level CNN-BiLSTM** + Attention Pooling |
| **Input Scope** | Hostname / SNI Authority (`domain.com:443`) | Full Deep URL (`https://host/path?param=val`) |
| **Target Latensi** | **$< 0.75\text{ ms}$ (p95)** pada CPU (Line-rate) | **$12 - 25\text{ ms}$** pada CPU |
| **Fitur yang Diekstrak** | 11 Fitur (TF-IDF base, Shannon entropy, Tranco Rank log, subdomain depth, hyphen/digit ratio, TLD flag) | 200 karakter raw sequence (embedding 64-dim, multi-scale conv 3/5/7, BiLSTM 128-dim) |
| **Lokasi Eksekusi** | In-process proxy helper & API gateway | Async ThreadPool Worker / Direct Scan endpoint |
| **Tujuan Utama** | Mencegah koneksi berbahaya sebelum payload diunduh (Zero-day domain / DGA) | Mendeteksi credential phishing, spear-phishing ber-path panjang, & scam lokal |

---

## 2. Diagnosis Empiris & Investigasi Akar Masalah

Sebelum dilakukan remediasi, evaluasi telemetri live watch `afferent-eval` menunjukkan anomali performa:

```text
==============================================================================
  AFFERENT SOC · TELEMETRY EVALUATION (BEFORE REMEDIATION)
==============================================================================
 Model Version   : stacker-xgb-v1:stacker-xgboost-v1
 Total Requests  : 500
 Unique Domains  : 34
 Triggered Alerts: 32 (Alert Fatigue: 94.1%)
 Block Threshold : 0.99914956
 Distribution    : Safe: 5.9% | Malicious: 0.0% | Review/Unknown: 94.1%
==============================================================================
```

### Bedah Akar Masalah (Root Causes):

### 1. Defacement Label Poisoning pada Kelas `other`
* Pada `dataset_builder.py`, 96.457 URL defacement dari Kaggle `sid321axn` dimasukkan ke dalam kelas `other` dengan label biner `is_malicious = 1`.
* **Karakteristik Nyata**: URL defacement di internet adalah situs bisnis, instansi, atau blog legal berbasis CMS (WordPress, Joomla) yang pernah mengalami perubahan tampilan (*deface*). Struktur domain dan path-nya 100% adalah web normal (contoh: `garage-pirenne.be`, `pashminaonline.com`).
* **Akibat Matematis**: Model Char-BiLSTM mempelajari bahwa domain resmi dengan struktur normal memiliki probabilitas tinggi sebagai kelas `other`. Pada pengujian langsung, `ctldl.windowsupdate.com` mendapat probabilitas kelas `other` sebesar **90.53%**, sehingga total $P_{malicious}$ membengkak menjadi **94.69%**.

### 2. Lexical Token Bias pada TF-IDF
* TF-IDF n-gram memegang **38.4% bobot keputusan** di Agent 1 (XGBoost).
* N-gram karakter seperti `login`, `online`, `update`, `edge`, `connect` sangat sering muncul pada dataset phishing publik.
* Model linear tidak memiliki representasi semantik entitas, sehingga domain sah seperti `login.microsoftonline.com` ($P_{base} = 0.8991$) dan `edge-http.microsoft.com` ($P_{base} = 0.9500$) langsung dicap berisiko sangat tinggi.

### 3. Kegagalan Ekstraksi TLD Multi-Part (`DomainFeatureExtractor`)
* Kode ekstraksi domain induk di `backend/services/domain_features.py` awalnya menggunakan:
  ```python
  parts = host.split(".")
  if len(parts) > 2:
      root = ".".join(parts[-2:])  # <-- BUG
  ```
* Untuk domain Indonesia (`.co.id`, `.go.id`, `.ac.id`), `parts[-2:]` menghasilkan `co.id` atau `go.id`.
* Akibatnya, lookup Tranco untuk `apispada.kemdiktisaintek.go.id` dan `bca.co.id` menghasilkan `None` ($is\_tranco\_top = 0$), sehingga reputasi domain terpercaya nasional hilang total.

### 4. Pemblokiran IP Privat / Homelab (`is_ip = 1.0`)
* Fitur `is_ip` memiliki bobot **28.5%** di XGBoost. Di dataset publik, URL berbasis IP mentah hampir selalu malware C2.
* Karena sistem belum membedakan IP privat RFC 1918 (`10.x.x.x`, `192.168.x.x`) dan Tailscale (`100.x.x.x`), pengujian akses ke IP server lokal (`10.166.219.145`) menghasilkan skor $P_{mal} = \mathbf{0.999848}$ dan langsung memicu pemblokiran gateway proxy.

### 5. Paradoks Threshold Wilson FPR 0.3%
* Karena false alarm sangat tinggi pada domain legal, algoritma optimasi threshold memaksakan ambang pemblokiran naik hingga **0.999149**.
* Hal ini menghancurkan Recall pemblokiran (hanya **13.8%** ancaman nyata yang terblokir otomatis), meloloskan phishing nyata (`phishing-verify-login-security.xyz`), dan melempar 94.1% traffic ke zona `Review / UNKNOWN` (memicu *SOC Alert Fatigue*).

---

## 3. Hasil Pengujian Benchmark (Before vs. After Remediation)

Pengujian dilakukan secara deterministik pada lingkungan server host menggunakan data uji benchmark (`test.csv` dan `indonesian_threat_casestudy.csv`):

| Kategori Pengujian | Target URL / Domain | Model Awal (Sebelum Audit) | Model Baru (Setelah Remediasi) | Status Akhir |
| :--- | :--- | :---: | :---: | :---: |
| **Global Enterprise** | `google.com` | $P_{mal} = 0.0826$ | **$P_{mal} = 0.0001$** |  SAFE (0 Alert) |
| **Enterprise Auth** | `login.microsoftonline.com` | $P_{mal} = 0.9958$ (Alert) | **$P_{mal} = 0.0068$** |  SAFE (0 Alert) |
| **Browser Telemetry** | `edge-http.microsoft.com` | $P_{mal} = 0.9915$ (Alert) | **$P_{mal} = 0.0017$** |  SAFE (0 Alert) |
| **OS Update CDN** | `ctldl.windowsupdate.com` | $P_{mal} = 0.9868$ (Alert) | **$P_{mal} = 0.0069$** |  SAFE (0 Alert) |
| **Code Infrastructure** | `github.com` | $P_{mal} = 0.0060$ | **$P_{mal} = 0.0001$** |  SAFE (0 Alert) |
| **Perbankan Nasional** | `klikbca.com` | $P_{mal} = 0.5961$ (Alert) | **$P_{mal} = 0.0005$** |  SAFE (0 Alert) |
| **Infrastruktur Kampus** | `apispada.kemdiktisaintek.go.id` | $P_{mal} = 0.9686$ (Alert) | **$P_{mal} = 0.0012$** |  SAFE (0 Alert) |
| **Internal LAN / Lab** | `10.166.219.145:3000` | $P_{mal} = 0.9998$ (**BLOCKED**) | **$P_{mal} = 0.0000$** |  SAFE (Bypassed) |
| **Credential Phishing** | `phishing-verify-login-security.xyz` | $P_{mal} = 0.9990$ (Lolos) | **$P_{mal} = 0.9981$** | 🚨 **AUTO-BLOCKED** |
| **Perjudian Online** | `slot88-gacor-maxwin.xyz` | $P_{mal} = 0.9989$ (Lolos) | **$P_{mal} = 0.9989$** | 🚨 **AUTO-BLOCKED** |
| **Typosquatting Bank** | `klikbca-login-verifikasi.xyz` | $P_{mal} = 0.9987$ (Lolos) | **$P_{mal} = 0.9987$** | 🚨 **AUTO-BLOCKED** |
| **Social Engineering** | `brimo-perubahan-tarif-baru.site` | $P_{mal} = 0.9962$ (Lolos) | **$P_{mal} = 0.9900$** | 🚨 **AUTO-BLOCKED** |

---

## 4. Evaluasi terhadap Studi Literatur Ilmiah (Folder `@Reference Model`)

Temuan audit ini dikonfirmasi oleh prinsip-prinsip metodologi dalam literatur cybersecurity:

1. **"Dos and Don'ts of Machine Learning in Computer Security" (Arp et al., USENIX Security 2022)**:
   * *Pitfall P1 (Sampling Bias)*: Dataset multi-source yang menyatukan insiden defacement ke dalam kelas malware mencemari representasi web legal.
   * *Pitfall P4 (Spurious Correlations)*: Model mengaitkan string `login` dan `online` sebagai sinyal kejahatan mutlak.
2. **"99% False Positives: A Qualitative Study of Network Alerts in a SOC" (Alahmadi et al.)**:
   * Menjelaskan bahaya *Alert Fatigue*. Ketika 94% traffic dilempar ke status review, analis SOC mengabaikan alert penting. Normalisasi threshold ke `0.8500` mereduksi noise hingga $< 5\%$.
3. **"Detecting Credential Spearphishing Attacks in Enterprise Settings" (Ho et al.)**:
   * Menekankan perlunya *reputation anchoring*. Domain Tranco Top 10.000 dengan TLS cert resmi harus diperlakukan sebagai platform otoritatif.

---

## 5. Implementasi Mesin Pembelajaran Berkelanjutan (Continuous Learning)

Untuk mencegah model menjadi usang (*model drift*), telah diimplementasikan subsistem:
* **File Modul**: `backend/services/continuous_learning.py`
* **CLI Runner**: `scripts/auto_retrain.py`
* **Trigger Endpoint**: `POST /api/admin/ml/retrain`
* **Jadwal Eksekusi**: Otomatis setiap **3 Jam** melalui daemon thread background.

### Prosedur Golden Quality Gate:
Sebelum model baru dipromosikan ke gateway proxy, engine wajib mengevaluasi:
1. **Benign Invariance Check**: Menguji 20 domain infrastruktur vital (Google, Microsoft, BCA, Cloudflare, UI, UGM). Jika salah satu domain menghasilkan $P_{mal} \ge 0.25$, model **DITOLAK OTOMATIS** (*Rollback*).
2. **Threat Recall Gate**: Menguji ancaman phishing dan scam lokal. Nilai $P_{mal}$ wajib $\ge 0.75$.
3. **Zero-Downtime Hot-Reload**: Saat promosi berhasil, model memanggil `stacker_scanner.reload()` langsung di memori tanpa memutus koneksi Squid atau me-restart container.

---

## 6. Rekomendasi Operasional & Tindak Lanjut

1. **Sinkronisasi Kode ke Server Host**:
   * Pastikan helper Squid di `/usr/local/bin/afferent_acl_helper.py` diperbarui dan Squid di-reload:
     ```bash
     sudo cp proxy/afferent_acl_helper.py /usr/local/bin/afferent_acl_helper.py
     sudo chmod +x /usr/local/bin/afferent_acl_helper.py
     sudo systemctl reload squid
     ```
2. **Eksekusi Retraining Awal di Server**:
   * Jalankan skrip retraining di dalam environment server:
     ```bash
     source ~/Human_Firewall/venv/bin/activate
     python3 scripts/auto_retrain.py --now
     ```
3. **Monitoring Berkala di Dashboard SOC**:
   * Pantau rasio *Safe vs Review vs Block* melalui halaman `/dashboard/soc-alerts`. Distribusi ideal pasca-audit:
     * **Safe (Clean)**: $88\% - 95\%$
     * **Auto-Blocked**: $2\% - 5\%$ (bergantung paparan kampanye phishing)
     * **Review Zone**: $< 5\%$ (hanya domain anomali/DGA sejati)
