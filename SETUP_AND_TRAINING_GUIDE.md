# Panduan Lengkap: Instalasi, Konfigurasi, Training Model, dan Deployment AFFERENT

Dokumen ini adalah panduan teknis langkah-demi-langkah untuk melakukan **fresh installation** proyek Human Firewall (AFFERENT) pada perangkat atau server baru (misal: homelab laptop/mini-PC, VM Linux Ubuntu Server, atau workstation Windows).

---

## 1. Prasyarat Sistem (System Prerequisites)

* **Sistem Operasi**: 
  * Direkomendasikan: Linux (Ubuntu Server 22.04 / 24.04 LTS, Debian 12).
  * Workstation: Windows 10/11 (mendukung PowerShell & Python langsung, atau via WSL2).
* **Hardware Minimum (Homelab Profile)**:
  * CPU: 4 Cores / 4–8 Threads (misal: Intel Core i5 Gen 8 / AMD Ryzen 3).
  * RAM: Minimal 8 GB (Direkomendasikan 12–16 GB).
  * Storage: SSD minimal 20 GB free space.
* **Perangkat Lunak Utama**:
  * **Git**: untuk clone repositori.
  * **Python 3.10 / 3.11 / 3.12 / 3.13** (pastikan `pip` dan `venv` terpasang).
  * **OpenSSL**: untuk pembuatan CA internal Squid.
  * **Squid Proxy 5.x / 6.x** dengan dukungan `--with-openssl` (paket `squid-openssl` di Ubuntu).

---

## 2. Langkah 1: Clone Repositori & Virtual Environment

Buka terminal/shell dan jalankan:

```bash
# 1. Clone repositori
git clone https://github.com/Llovind/Human_Firewall.git
cd Human_Firewall

# 2. Buat Python Virtual Environment (Sangat disarankan agar dependensi terisolasi)
python -m venv venv

# 3. Aktifkan Virtual Environment
# Di Linux / macOS:
source venv/bin/activate

# Di Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

---

## 3. Langkah 2: Instalasi Dependensi Python

AFFERENT memisahkan dependensi dasar web backend dan dependensi berat Machine Learning:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependensi dasar web/API
pip install -r backend/requirements.txt

# Install dependensi Machine Learning (PyTorch, scikit-learn, joblib, dll)
pip install -r backend/requirements-ml.txt

# Install XGBoost & dependensi data khusus
pip install xgboost tldextract pandas numpy
```

---

## 4. Langkah 3: Pemisahan Kredensial & Konfigurasi Lingkungan (`.env`)

> [!IMPORTANT]
> **Prinsip Keamanan**: Kredensial asli, password, dan secret key **TIDAK BOLEH** disimpan di Git. Gunakan file template `.env.example` untuk menghasilkan file `.env` lokal Anda.

### 4.1. Salin Template File Lingkungan
```bash
cp .env.example .env
```
*(Di Windows PowerShell gunakan: `Copy-Item .env.example .env`)*

### 4.2. Generate Secret Key Secara Acak
Buka terminal Python untuk menghasilkan string acak aman:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32)); print('PROXY_IDENTITY_PEPPER=' + secrets.token_urlsafe(32)); print('AUTH_AUDIT_PEPPER=' + secrets.token_urlsafe(32)); print('ML_WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

### 4.3. Sesuaikan Variabel Kunci di `.env`
Buka file `.env` menggunakan teks editor (misal: `nano .env` atau VS Code) dan sesuaikan:

```ini
# =============================================================================
# RUNTIME & SECURITY
# =============================================================================
APP_ENV=production
FLASK_DEBUG=false
SECRET_KEY=<paste_random_secret_dari_langkah_4.2>
ADMIN_PASSWORD=PasswordAdminKuat123!
BOOTSTRAP_ADMIN_EMAIL=admin@humanfirewall.local

# Pepper untuk audit dan hashing IP klien
PROXY_IDENTITY_PEPPER=<paste_random_pepper_dari_langkah_4.2>
AUTH_AUDIT_PEPPER=<paste_random_pepper_dari_langkah_4.2>
ML_WEBHOOK_SECRET=<paste_random_secret_dari_langkah_4.2>

# =============================================================================
# URL & NETWORKING BIND
# =============================================================================
# Ganti 127.0.0.1 dengan IP LAN server jika diakses device lain di jaringan
WEB_BIND_IP=127.0.0.1
NEXT_PUBLIC_BASE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://127.0.0.1:5000

# =============================================================================
# ML & PROXY ENGINE CONFIGURATION
# =============================================================================
ML_LOCAL_ENABLED=true
# Path ke model lokal (relatif atau absolut)
ML_DOMAIN_MODEL_DIR=backend/models/domain_v3
ML_STACKER_MODEL_DIR=backend/models/stacker_v1
TRANCO_CSV_PATH=dataset/raw/tranco/tranco_Y8YYG.csv
ML_CPU_THREADS=4
ML_BLOCK_CONFIDENCE_THRESHOLD=0.85
ML_ALLOW_CONFIDENCE_THRESHOLD=0.80

# Database SQLite lokal
DB_PATH=backend/instance/human_firewall.db
```

---

## 5. Langkah 4: Setup Sertifikat SSL Squid CA (Bump-on-Deny)

AFFERENT menggunakan arsitektur **No-Decrypt TLS**:
* Traffic normal yang aman di-**`splice`** (koneksi murni langsung lewat tanpa dibaca/didekripsi oleh proxy).
* Hanya koneksi yang terbukti dilarang/malicious yang di-**`bump`** secara lokal menggunakan CA internal untuk menyajikan halaman HTML *"Blocked by AFFERENT"*.

### 5.1. Generate CA Root Internal
Jalankan perintah OpenSSL berikut untuk membuat root certificate CA AFFERENT:

```bash
mkdir -p proxy/ssl_cert
cd proxy/ssl_cert

# Buat private key CA
openssl genrsa -out afferent-proxy-ca.key 2048

# Buat sertifikat CA publik (valid 5 tahun)
openssl req -new -x509 -days 1825 -key afferent-proxy-ca.key -out afferent-proxy-ca.crt \
    -subj "/C=ID/ST=Jakarta/O=Afferent Security Lab/CN=Afferent Inspection CA"

# Amankan izin file private key
chmod 400 afferent-proxy-ca.key
cd ../..
```

### 5.2. Pasang Sertifikat di Klien (Browser / OS)
Agar browser tidak menampilkan peringatan sertifikat saat dialihkan ke halaman blokir:
* **Windows**: Buka `afferent-proxy-ca.crt` $\rightarrow$ Install Certificate $\rightarrow$ Place in **"Trusted Root Certification Authorities"**.
* **Ubuntu/Debian**: Salin `afferent-proxy-ca.crt` ke `/usr/local/share/ca-certificates/` lalu jalankan `sudo update-ca-certificates`.

---

## 6. Langkah 5: Persiapan Data & Tranco Top Sites

Dataset telah terstruktur di direktori `dataset/`:
* `dataset/raw/tranco/tranco_Y8YYG.csv`: Berisi 50.000 daftar domain terpopuler dunia dari Tranco.
* `dataset/processed/train.csv`: Data training yang telah bersih dari data-leakage.
* `dataset/processed/val.csv`: Data validasi untuk threshold policy & kalibrasi.
* `dataset/processed/test.csv`: Data holdout evaluasi akhir.

Jika Anda memulai dari repository kosong tanpa dataset processed, jalankan builder:
```bash
python dataset_builder.py
```

---

## 7. Langkah 6: Pipeline Training Model (Dari Nol Sampai Model Jadi)

### Tahap 6.1: Training Base Model TF-IDF (`domain_v3`)
Model ini melatih ekstraksi character n-gram (2–5) dengan Logistic Regression terkalibrasi Platt scaling:

```bash
python backend/train_domain_model.py \
    --dataset dataset/processed \
    --output backend/models/domain_v3 \
    --fpr-budget 0.003
```
* **Output yang dihasilkan**:
  * `backend/models/domain_v3/classifier.joblib` (Model pipeline & calibrator).
  * `backend/models/domain_v3/manifest.json` (Laporan evaluasi FPR & latency).

### Tahap 6.2: Training Stacker Meta-Learner XGBoost (`stacker_v1`)
Model ini menggabungkan probabilitas TF-IDF, Shannon Entropy, fitur leksikal, dan Tranco Rank:

```bash
python backend/train_stacker_model.py \
    --dataset dataset/processed \
    --base-model backend/models/domain_v3/classifier.joblib \
    --tranco dataset/raw/tranco/tranco_Y8YYG.csv \
    --output backend/models/stacker_v1 \
    --fpr-budget 0.003
```
* **Output yang dihasilkan**:
  * `backend/models/stacker_v1/stacker.joblib` (Model ensemble XGBoost, ukuran hanya ~52 KB).
  * `backend/models/stacker_v1/manifest.json` (Metrik presisi 99.95% & FPR 0.14%).

---

## 8. Langkah 7: Verifikasi & Smoke Test (Model Works Validation)

Untuk memastikan seluruh pipeline inferensi bekerja secara instan (< 1ms per host):

### 8.1. Uji Inferensi Langsung Menggunakan Python Shell
```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from services import stacker_scanner

stacker_scanner.warmup()
print('Status Stacker:', stacker_scanner.status())

# Test domain phishing simulasi
res_phish = stacker_scanner.scan('login.secure-bank.bca-verifikasi.xyz')
print('Test Phish Result :', res_phish['verdict'], '| P_mal:', res_phish.get('prob_malicious'))

# Test domain aman
res_safe = stacker_scanner.scan('google.com')
print('Test Safe Result  :', res_safe['verdict'], '| P_mal:', res_safe.get('prob_malicious'))
"
```
**Ekspektasi Output**:
* `login.secure-bank.bca-verifikasi.xyz` $\rightarrow$ `verdict=malicious`, `P_mal >= 0.99` (Auto-Block!).
* `google.com` $\rightarrow$ `verdict=safe`, `P_mal < 0.10`.

### 8.2. Jalankan Automated Regression Test Suites
Pastikan tidak ada policy logic yang rusak:
```bash
# 1. Uji Proxy Gate (evaluasi domain-only, pendings, overrides)
python backend/test_proxy_gate.py

# 2. Uji Integrasi Runtime Lokal
python backend/test_local_suite.py
```
*(Seluruh tes wajib berstatus **OK**).*

---

## 9. Langkah 8: Menjalankan Sistem Runtime

### 9.1. Inisialisasi Database
```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from database import init_db
init_db()
print('Database initialized.')
"
```

### 9.2. Menjalankan Backend API Flask
```bash
# Set environment
export FLASK_APP=backend/app.py
# Di Windows PowerShell: $env:FLASK_APP="backend/app.py"

python backend/app.py
```
Backend API sekarang mendengarkan di `http://127.0.0.1:5000`.

### 9.3. Menjalankan Squid Proxy (Jika Dideploy Sebagai Server)
Jika Squid dipasang di mesin Linux yang sama:
```bash
# 1. Salin konfigurasi squid
sudo cp proxy/squid.conf /etc/squid/squid.conf

# 2. Salin helper external ACL
sudo cp proxy/afferent_acl_helper.py /usr/local/bin/afferent_acl_helper.py
sudo chmod +x /usr/local/bin/afferent_acl_helper.py

# 3. Inisialisasi SSL database certgen
sudo /usr/lib/squid/security_file_certgen -c -s /var/lib/squid/ssl_db -M 4MB
sudo chown -R proxy:proxy /var/lib/squid/ssl_db

# 4. Restart Squid
sudo systemctl restart squid
sudo systemctl status squid
```

---

## 10. Ringkasan File & Struktur Direktori Model

```text
Human_Firewall/
├── .env                          <-- Konfigurasi rahasia lokal (JANGAN DICOMMIT)
├── .env.example                  <-- Template konfigurasi bersih
├── dataset/
│   ├── processed/                <-- Dataset train/val/test CSV
│   └── raw/tranco/               <-- File tranco_Y8YYG.csv
├── backend/
│   ├── app.py                    <-- Flask application entrypoint
│   ├── train_domain_model.py     <-- Script training Base TF-IDF
│   ├── train_stacker_model.py    <-- Script training Stacker XGBoost
│   ├── services/
│   │   ├── domain_features.py    <-- Ekstraktor fitur leksikal & Tranco
│   │   ├── stacker_scanner.py    <-- Service scanner runtime XGBoost
│   │   └── ml_service.py         <-- Routing keputusan proxy
│   └── models/
│       ├── domain_v3/            <-- Artifact Base TF-IDF
│       └── stacker_v1/           <-- Artifact Stacker XGBoost (stacker.joblib)
└── proxy/
    ├── squid.conf                <-- Konfigurasi Squid (splice all / bump deny)
    └── afferent_acl_helper.py    <-- External ACL helper Squid
```
