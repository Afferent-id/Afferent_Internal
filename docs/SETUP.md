# Setup developer

Panduan ini melengkapi [README_SETUP.md](../README_SETUP.md) (setup lab dari clone baru) dengan fokus pada
developer yang ingin menjalankan dan mengubah kode. Bagian **Hasil verifikasi** mencatat apa yang benar-benar
dijalankan pada 2026-10-10 di macOS (Darwin 25.5, Python 3.14.7, Node 26.5.0, npm 11.17.0, Docker 29.7.2).

## 1. Prasyarat

| Kebutuhan | Versi | Untuk |
| --- | --- | --- |
| Git | bebas | clone |
| Docker + Compose v2 | Compose file memakai `image: postgres:17`, `redis:7`, dll. | menjalankan seluruh stack (jalur utama) |
| Python | 3.10+ untuk `scripts/setup_lab.py`; image backend memakai 3.10 | setup helper, tes backend lokal |
| Node.js | 22+ (README_SETUP); next 16.3.8 | dashboard lokal, lint, tes, build |
| GPU NVIDIA + Docker GPU | opsional | hanya profile `llm` (Ollama) |

`TODO: konfirmasi ke tim` versi minimum Node yang diuji (README_SETUP menyebut 22+; verifikasi di bawah memakai 26).

## 2. Instalasi

### Stack penuh (Docker) — jalur resmi

```sh
git clone git@github.com:Afferent-id/Afferent_Internal.git
cd Afferent_Internal
python scripts/setup_lab.py --server-host 127.0.0.1          # buat .env + .env.proxy.local
python scripts/setup_lab.py --certificates --server-host 127.0.0.1   # buat CA lab di secrets/
docker compose up -d --build gophish mailpit
# ambil API key GoPhish -> isi GOPHISH_API_KEY di .env  (lihat README_SETUP.md §2)
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Helper **menolak menimpa** ENV/PKI yang ada dan bukan alat rotasi. Jangan jalankan di instalasi yang sudah berisi data demo.
Jangan pernah `docker compose down -v` pada instalasi yang berisi riwayat demo (menghapus volume).

### Backend tanpa Docker (untuk menjalankan tes)

```sh
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# requirements-ml.txt (torch 2.8.0+cpu) hanya perlu untuk fitur ML; lihat "Hasil verifikasi"
```

### Dashboard

```sh
cd dashboard
npm ci
```

## 3. Variabel lingkungan

Sumber: [.env.example](../.env.example). Hanya **nama dan fungsi** yang dicantumkan; nilai rahasia dibangkitkan
`scripts/setup_lab.py` dan tidak boleh di-commit (`.env`, `.env.*`, `secrets/` ada di `.gitignore`).
Flask menolak start bila `ADMIN_PASSWORD`, `SECRET_KEY`, atau `SERVICE_API_KEY` kosong.

**Runtime & keamanan**

| Variabel | Fungsi |
| --- | --- |
| `APP_ENV`, `NODE_ENV` | Mode runtime; staging/production menolak konfigurasi tidak aman |
| `DEV_BYPASS_AUTH`, `FLASK_DEBUG` | Hanya untuk workstation lokal; harus `false` selain itu |
| `SECRET_KEY` | Kunci session Flask (wajib) |
| `SERVICE_API_KEY` | Bearer untuk panggilan antar-layanan (Squid helper, BFF) (wajib) |
| `ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_EMAIL` | Bootstrap satu kali akun administrator; sesudahnya password ada di DB |
| `OTP_PEPPER`, `AUTH_AUDIT_PEPPER`, `PROXY_IDENTITY_PEPPER` | Pepper hashing OTP / audit login / identitas perangkat proxy |
| `ALLOWED_ORIGINS` | Origin dashboard yang diizinkan CORS (hostname harus persis seperti di browser) |
| `TRUST_PROXY_HEADERS` | Percaya `X-Forwarded-For` |
| `AUTH_COOKIE_SECURE` | Flag `Secure` pada cookie (false untuk lab HTTP) |
| `AUTH_SESSION_TTL_SECONDS`, `PASSWORD_MIN_LENGTH` | Masa berlaku login (default 86400) dan panjang password minimum |

**URL & binding**: `WEB_BIND_IP`, `PROXY_BIND_IP`, `MAILPIT_BIND_IP`, `GOPHISH_ADMIN_BIND_IP` (alamat bind host);
`NEXT_PUBLIC_BASE_URL`, `NEXT_PUBLIC_API_URL`, `API_URL`, `SERVER_BASE_URL`, `SIMULATION_BASE_URL`,
`GOPHISH_PHISH_PUBLIC_URL`, `GOPHISH_ADMIN_PUBLIC_URL`, `MAILPIT_PUBLIC_URL`, `SIMULATION_EDUCATION_URL`, `PROXY_PORTAL_URL` (URL yang dilihat browser/klien).

**Email/OTP**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`, `SMTP_SECURITY`, `SMTP_TIMEOUT_SECONDS`, `REAL_SMTP_ENABLED` (SMTP nyata di luar scope);
`OTP_EXPIRY_SECONDS`, `OTP_MAX_ATTEMPTS`, `OTP_RESEND_COOLDOWN_SECONDS`, `OTP_RATE_LIMIT_WINDOW_SECONDS`, `OTP_MAX_REQUESTS_PER_WINDOW`;
`EDUCATION_EMAIL_ENABLED`, `EDUCATION_AUTO_ENABLED`, `EDUCATION_SCORE_THRESHOLD`, `EDUCATION_COOLDOWN_SECONDS`; `SEVERE_INCIDENT_EMAIL_ENABLED`.

**Proxy**: `PROXY_PORT`, `PUBLIC_PROXY_URL`, `PUBLIC_PROXY_PROBE_URL`, `PROXY_FAIL_MODE` (`closed`/`open`),
`PROXY_DECISION_TIMEOUT_SECONDS`, `PROXY_ENFORCEMENT_API_URL`, `PROXY_REVOCATION_INTERVAL_SECONDS`, `PROXY_MAX_CONNECTIONS`,
`PROXY_DEVICE_TTL_SECONDS`, `PROXY_CONNECTED_WINDOW_SECONDS`, `PROXY_BOOTSTRAP_ALLOW_DOMAINS`, `PROXY_ML_VERDICT_TTL_SECONDS`,
`PROXY_ML_CACHE_TTL_SECONDS`, `PROXY_SOC_CACHE_TTL_SECONDS`, `PROXY_UNKNOWN_RETRY_SECONDS`, `PROXY_IDEMPOTENCY_TTL_SECONDS`,
`PROXY_TRAFFIC_RETENTION_DAYS`, `PROXY_AUDIT_RETENTION_DAYS`. Rahasia PostgreSQL/Redis (`PROXY_DB_NAME`, `PROXY_DB_USER`, `PROXY_DB_PASSWORD`, `REDIS_PASSWORD`) dan
`ML_WEBHOOK_SECRET` ditulis helper ke `.env.proxy.local`. `PROXY_FEATURE_ENABLED` (mengaktifkan runtime proxy di [app.py](../backend/app.py)) tidak ada di `.env.example`;
nilainya di-hardcode `true` di `docker-compose.yml`.

**ML**: `ML_SCANNER_URL` (ML eksternal HMAC, opsional), `ML_LOCAL_ENABLED`, `ML_DOMAIN_MODEL_DIR`, `ML_CPU_THREADS`, `ML_URL_CACHE_TTL_SECONDS`,
`ML_TLS_CA_BUNDLE`, `ML_SCANNER_TIMEOUT_SECONDS`, `ML_BLOCK_CONFIDENCE_THRESHOLD`, `ML_ALLOW_CONFIDENCE_THRESHOLD`.

**Data & GoPhish**: `DB_PATH` (file SQLite), `GOPHISH_API_KEY`, `GOPHISH_API_URL`, `GOPHISH_CERT_DIR`, `GOPHISH_CA_BUNDLE`, `GOPHISH_SYNC_ENABLED`.

**Integrasi opsional**: `VT_API_KEY`, `URLSCAN_API_KEY`, `VT_REQUESTS_PER_MINUTE` (kuota VirusTotal bersama), `FILE_SCAN_MAX_MB`, `FILE_SCAN_RETENTION_SECONDS`,
`FIRECRAWL_API_KEY` (kloning halaman kampanye), `GEMINI_API_KEY`, `GROQ_API_KEY`, `GROQ_MODEL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `AI_HEATMAP_USE_LLM`,
Live traffic hanya memakai ML lokal; local LLM telah dipensiunkan dari Compose.
VT/urlscan tidak dipanggil untuk traffic proxy, termasuk di background.

**Dashboard saja**: `USE_MOCKS=true` (dengan `npm run dev:mock`, hanya di `next dev`); `scripts/validate-runtime-env.mjs` dijalankan sebelum `npm start`.

## 4. Menjalankan secara lokal

| Tujuan | Perintah |
| --- | --- |
| Seluruh stack | `docker compose up -d --build` lalu buka dashboard `http://127.0.0.1:3000` |
| OTP / email | Mailpit `http://127.0.0.1:8025` (email tidak sampai ke Gmail) |
| GoPhish admin | `https://localhost:3333` (percayai CA lab publik di `secrets/gophish-pki/`) |
| Dashboard saja, tanpa backend | `cd dashboard && npm run dev:mock` (data palsu; ganti role/skenario lewat switcher mock) |
| Dashboard dev + backend nyata | `cd dashboard && npm run dev` dengan `API_URL` mengarah ke Flask |
| Hentikan | `docker compose stop` |

Akun: administrator dari `BOOTSTRAP_ADMIN_EMAIL`/`ADMIN_PASSWORD`; buat akun employee dan SOC terpisah lewat dashboard.
`TODO: konfirmasi ke tim` cara resmi membuat akun role `soc`/`grc`/`ciso` untuk developer baru (lihat `auth_service.create_account` dan [seed_data.py](../backend/seed_data.py)).

## 5. Menjalankan tes

```sh
# Guard repo (tidak mencetak nilai rahasia)
node scripts/check_submission.cjs
python scripts/test_setup_lab.py

# Dashboard
cd dashboard && npm run lint && npm test && npm run build

# Backend: jalankan SATU FILE per proses
cd backend
python -m unittest test_local_suite
python -m unittest test_phase1_auth      # dst. untuk setiap test_*.py
```

> **Penting:** `python -m unittest discover` di `backend/` memberi hasil palsu-gagal karena tiap modul tes
> menyetel `os.environ`/DB sementara sendiri saat di-import. Jalankan per file seperti `docs/FINAL_SUBMISSION.md`
> (yang memakai `docker run --network none ... python -m unittest <modul>` pada image backend).

Tes lain: `proxy/test_error_page.py` dan `proxy/test_selective_tls.py` (butuh Squid terpasang, jalankan di image proxy),
`ml/local_llm/test_*.py` (butuh `tldextract` dll.), `test_proxy_runtime.py` (butuh PostgreSQL + Redis nyata; otomatis di-skip),
`test_mailpit_warning.py` (skrip smoke Mailpit, bukan unittest).

## 6. Hasil verifikasi (2026-10-10)

| Langkah | Hasil |
| --- | --- |
| `node scripts/check_submission.cjs` | ✅ 826 file, 0 perlu perhatian |
| `python3 scripts/test_setup_lab.py` | ✅ 2 tes OK |
| `npm ci` (dashboard) | ✅ berhasil; peringatan: skrip install `unrs-resolver` belum disetujui (`npm approve-scripts`), `npm audit` melaporkan 7 kerentanan *high* |
| `npm run lint` | ✅ bersih (`--max-warnings=0`) |
| `npm test` | ✅ 4 skrip PASS |
| `npm run build` | ✅ build sukses |
| Backend, `pip install -r requirements.txt` (venv Python 3.14) | ✅ terpasang |
| Backend, `pip install -r requirements-ml.txt` | ❌ **gagal**: `torch==2.8.0+cpu` tidak tersedia untuk macOS/Python 3.14 (hanya 2.9.0+ pada indeks). Image Docker (Python 3.10, Linux) tidak terdampak, tetapi tidak diuji karena daemon Docker mati |
| Backend, tiap `test_*.py` dijalankan terpisah | ✅ 18 file OK (`test_proxy_runtime` 4 skipped) |
| `test_mailpit_warning.py` | ⚠️ "0 tests" (skrip, bukan unittest) |
| `test_char_bilstm_scanner.py` | ❌ gagal tanpa env (`ADMIN_PASSWORD` tidak diset oleh tes ini), tanpa torch, dan 2 tes menerima 401 — tes ini tidak menyetel auth/env seperti tes lain dan tidak ada di daftar `FINAL_SUBMISSION.md` |
| `python -m unittest discover` di `backend/` | ❌ 6 gagal / 8 error (efek bersama modul tes, lihat catatan §5) |
| `proxy/test_error_page` + `test_selective_tls` di host | ❌ `/etc/squid/squid.conf` tidak ada (hanya jalan dalam image proxy) |
| `ml/local_llm` tes di host | ❌ `ModuleNotFoundError: tldextract` (tidak ada requirements file di folder itu) |
| `docker compose config --quiet` | ⚠️ valid, tetapi memberi peringatan variabel kosong karena `.env` belum ada |
| `docker compose up` / seluruh stack | ⛔ **tidak dijalankan** — daemon Docker tidak aktif; alur E2E, GoPhish, Squid, Postgres/Redis belum diverifikasi |
| `python scripts/setup_lab.py` | ⛔ tidak dijalankan agar tidak membuat `.env`/CA di checkout kerja pengguna |

## 7. Troubleshooting singkat

- Flask langsung exit saat boot → periksa `ADMIN_PASSWORD`, `SECRET_KEY`, `SERVICE_API_KEY`; dengan proxy aktif juga `ML_WEBHOOK_SECRET` dan `PROXY_IDENTITY_PEPPER`.
- Login terus mental di lab LAN → `ALLOWED_ORIGINS` harus memuat hostname persis yang diketik di browser (`localhost` ≠ `127.0.0.1`).
- Panduan jaringan/VM: [DEMO_VM_SOC.md](DEMO_VM_SOC.md).
