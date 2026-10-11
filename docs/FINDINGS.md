# Temuan analisis codebase

Hasil pembacaan repo pada commit `c6bd8ef` (branch `development`) dan eksekusi pemeriksaan pada 2026-10-10
(detail di [SETUP.md](SETUP.md) §6). Ini bukan audit keamanan penuh. Tingkat: **Tinggi / Sedang / Rendah**.
Bukti disebut dengan file/perintah; yang belum bisa dipastikan ditandai `TODO: konfirmasi ke tim`.

## A. Risiko keamanan

| # | Tingkat | Temuan | Bukti | Tindakan yang disarankan |
| --- | --- | --- | --- | --- |
| S1 | **Tinggi** | **Token bot Telegram pernah ter-commit dan masih ada di riwayat git.** Ditambahkan di `6e59817` (sebagai baris ENV dan literal di skrip), dihapus di `4bd8180`, ditambahkan lagi di `364976d`, dihapus di `7e0c0a3`. Tidak ada di HEAD. | Pemindaian `git show <commit>` dengan pola token Telegram; nilai sengaja tidak dicetak di sini | Anggap bocor: pastikan token dicabut/dirotasi di BotFather (`TODO: konfirmasi ke tim` apakah sudah). Bot Telegram sudah dipensiunkan, jadi cukup revoke. Bila repo akan publik, bersihkan riwayat (`git filter-repo`) — merusak hash, koordinasikan dulu |
| S2 | Sedang | Pemindaian lain di HEAD dan riwayat (kunci Google/Groq/OpenRouter, private key, file `.env`/`.key`/`.pem`/`.db` yang ditambahkan) **tidak menemukan** apa pun; `scripts/check_submission.cjs` lulus (826 file). Pemindaian riwayat hanya untuk pola yang diketahui | — | Jadwalkan scanner rahasia penuh (mis. gitleaks/trufflehog) sebagai pemeriksaan rutin; `check_submission.cjs` sendiri menyatakan bukan audit riwayat |
| S3 | Sedang | Artefak model dimuat dengan deserializer yang bisa mengeksekusi kode bila file diganti: `pickle.load` ([char_bilstm_scanner.py:164](../backend/char_bilstm_scanner.py)), `joblib.load` ([domain_scanner.py:50](../backend/services/domain_scanner.py)). `torch.load` sudah `weights_only=True` | Biner terlacak di git: `calibrators.pkl`, `classifier.joblib`, `char_bilstm.pt` | Verifikasi hash terhadap `manifest.json` sebelum memuat; batasi siapa yang boleh mengubah `backend/models/` |
| S4 | Sedang | Endpoint debug tertinggal: `POST /api/debug/vt` (role `soc`) mengembalikan respons mentah VirusTotal | [routes/threat.py:102](../backend/routes/threat.py) | Hapus atau gerbangkan dengan flag dev |
| S5 | Sedang | `POST /api/threat/scan-dl` dan `GET /api/threat/stats` tidak memakai `@require_roles`; terlindungi hanya oleh gerbang `before_request` (semua role terautentikasi, termasuk employee, bisa memanggil). Mungkin disengaja | [routes/threat.py:115](../backend/routes/threat.py) | `TODO: konfirmasi ke tim` apakah employee boleh; tambahkan `require_roles` eksplisit |
| S6 | Sedang | Default lab tidak aman untuk internet: `AUTH_COOKIE_SECURE=false` (HTTP), `TRUST_PROXY_HEADERS=true`, `PROXY_BIND_IP`/`WEB_BIND_IP` disarankan `0.0.0.0` untuk VM, SMTP tanpa TLS. Dokumen sudah menyebut "kompromi lab" | `.env.example`, [README_SETUP.md](../README_SETUP.md) | Jangan deploy ke jaringan publik; siapkan profil produksi (lihat branch `feature/vps-deployment`) |
| S7 | Sedang | `npm audit` pada dashboard melaporkan **7 kerentanan high** (antara lain `sharp <0.35.5`) | `npm audit` 2026-10-10 | Tinjau `npm audit`, naikkan dependensi, pertimbangkan `npm approve-scripts` untuk `unrs-resolver` |
| S8 | Rendah | Kunci privat CA proxy dipasang ke container dari `./proxy/ssl` dan CA GoPhish dari `secrets/`; keduanya di-`.gitignore`, perlindungan hanya izin OS | [docker-compose.yml](../docker-compose.yml) | Batasi izin file; jangan salin ke lokasi yang disinkronkan (cloud drive) |
| S9 | Rendah | Squid `http_access allow all` setelah ACL; `Safe_ports` mengizinkan 1025-65535 | [proxy/squid.conf](../proxy/squid.conf) | `TODO: konfirmasi ke tim` apakah rentang port ini perlu dipersempit |
| S10 | Rendah | Proteksi: cookie session `httpOnly`, `sameSite=lax`; gerbang deny-by-default; HMAC untuk webhook ML. Catatan: HMAC `X-Afferent-Signature` hanya menandatangani body (tanpa timestamp/nonce), sehingga request yang tertangkap bisa diputar ulang | [proxy_service.py:315](../backend/services/proxy_service.py) | Tambahkan timestamp+nonce bila webhook ML eksternal dipakai |

## B. Dead code / sisa yang tidak terpakai

| # | Temuan | Bukti |
| --- | --- | --- |
| D1 | [backend/docker-entrypoint.sh](../backend/docker-entrypoint.sh) tidak direferensikan Dockerfile maupun Compose, dan memakai `gosu` serta `flask run` yang tidak dipasang/dipakai image (Dockerfile memakai gunicorn) | `grep docker-entrypoint` di Dockerfile/compose kosong |
| D2 | Template tanpa referensi dari kode Python: `personal_dashboard.html`, `personal_dashboard_error.html`, `spot_the_fake_real.html`, `visit.html` (route `/visit` dan `/go` sudah `410`). Mungkin dirujuk lewat cara dinamis — `TODO: konfirmasi ke tim` | `grep "<nama>.html" backend --include=*.py` |
| D3 | Route yang dipensiunkan masih terdaftar dan hanya mengembalikan `410`: `/api/auth/admin`, `/api/telegram/command`, `/api/auth/validate-token`, `/api/register-telegram`, `/api/telegram/user`, `/visit`, `/go`, `/admin/login`, `/admin/logout`; dan `/api/threat/analyze` (gateway ML/VT era Telegram) | [routes/auth.py](../backend/routes/auth.py), [routes/events.py](../backend/routes/events.py), [routes/proxy.py](../backend/routes/proxy.py) |
| D4 | Rute ganda tanpa dan dengan prefiks `/admin` untuk fungsi sama (`/api/leaderboard` & `/api/admin/leaderboard`, `login-history`, `compliance-summary`, `threats/feed`, `threats/action`, `policy/*`, `ai/summaries`) | [routes/admin_api.py](../backend/routes/admin_api.py) |
| D5 | `ROLE_ROUTES` di halaman utama memuat role `admin`, padahal `VALID_ROLES` backend tidak punya role itu; `/admin` hanya mengalihkan ke phishing-admin | [dashboard/src/app/page.tsx:26](../dashboard/src/app/page.tsx), [auth_service.py:23](../backend/services/auth_service.py) |
| D6 | Berkas liar di dalam `dashboard/src/app/`: folder ber-UUID `1877eb81-…/implementation_plan.md` dan `walkthrough.md` (bukan route/halaman); `dashboard/implementation_plan.md` | `git ls-files dashboard` |
| D7 | `backend/.DS_Store` ter-commit; `.DS_Store` lain tidak terlacak tetapi tidak ada di `.gitignore` | `git ls-files \| grep DS_Store` |
| D8 | `app.py` masih menyediakan `GET /` yang merender `dashboard.html` (UI Flask lama) di samping dashboard Next.js; `app.run(host='0.0.0.0')` hanya untuk dev | [backend/app.py](../backend/app.py) |
| D9 | `dataset_builder.py` (44 KB) berada di root repo, di luar `dataset/` atau `ml/` | — |

## C. Fitur setengah jadi / belum selesai

| # | Temuan | Bukti |
| --- | --- | --- |
| F1 | Model domain v3: recall keseluruhan 21,18%; kategori judol/adult belum punya dataset terverifikasi (OOD judol 0/70 Block). Checklist resmi mencatat ini belum selesai | [TECHNICAL_DEBT_CHECKLIST.md](TECHNICAL_DEBT_CHECKLIST.md) |
| F2 | LLM lokal hasil fine-tune belum lolos gerbang promosi dan tidak dimuat sebagai model aktif | [LOCAL_LLM_EVALUATION.md](LOCAL_LLM_EVALUATION.md), [README_SETUP.md](../README_SETUP.md) |
| F3 | Uji browser VM + host dan tampilan baru ("oleh Daf") belum dicentang | [TECHNICAL_DEBT_CHECKLIST.md](TECHNICAL_DEBT_CHECKLIST.md) |
| F4 | SMTP nyata dan sensor NAC dinyatakan Future Work; `REAL_SMTP_ENABLED` ada di ENV | `.env.example`, [README.md](../README.md) |
| F5 | Dua lini model URL yang tumpang tindih: Char-BiLSTM (`/api/threat/scan-dl`) vs model domain v3 (proxy). Status Char-BiLSTM dalam produk tidak jelas — `TODO: konfirmasi ke tim` | [routes/threat.py](../backend/routes/threat.py), [services/domain_scanner.py](../backend/services/domain_scanner.py) |
| F6 | Jalur ML webhook eksternal (`ML_SCANNER_URL`, HMAC) ada tetapi default kosong; `test_proxy_runtime.py` (butuh Postgres+Redis) otomatis di-skip sehingga jalur proxy runtime tidak tercakup tes otomatis lokal | [test_proxy_runtime.py](../backend/test_proxy_runtime.py) |
| F7 | Branch `feature/vps-deployment` dan `docs/prd-srs-internal` ada di luar `development`; status deployment VPS tidak terdokumentasi di sini | `git branch -a` |

## D. Kualitas, tes, dan operasional

| # | Temuan |
| --- | --- |
| Q1 | `requirements-ml.txt` memaku `torch==2.8.0+cpu`: tidak terpasang di macOS / Python 3.14 (hanya Linux/Windows + versi Python yang didukung). Developer Mac tidak bisa menjalankan fitur ML di luar Docker |
| Q2 | `test_char_bilstm_scanner.py` gagal di luar environment khusus: tidak menyetel env seperti tes lain, memanggil endpoint tanpa autentikasi (401), dan tidak ada dalam daftar tes resmi |
| Q3 | `python -m unittest discover` tidak dapat dipakai karena modul tes saling mencemari `os.environ`/DB; tidak ada runner tunggal atau CI (`.github/` tidak ada) |
| Q4 | `test_mailpit_warning.py` bernama seperti tes tetapi berupa skrip (0 tes); `ml/local_llm/test_*.py` butuh `tldextract` yang tidak dideklarasikan; tes `proxy/` hanya jalan di dalam image |
| Q5 | `backend/database.py` 3,7 rb baris berisi skema, migrasi, dan semua query dalam satu modul |
| Q6 | Repo berat: `.git` ±289 MB, `dataset/` ±113 MB terlacak, biner model dan `AFFERENT_deck_full.pptx` ter-commit; vault `Obsidian/` (±104 MB) tidak terlacak tetapi juga tidak di-ignore (risiko ter-commit tak sengaja) |
| Q7 | Inkonsistensi penamaan: folder lokal `afferent`, repo `Human_Firewall`, image `human_firewall-flask_api`, container `hfl-*`, produk "AFFERENT" |
| Q8 | `docker compose up` / E2E **belum diverifikasi** dalam analisis ini karena daemon Docker tidak aktif |
| Q9 | Setelah analisis dimulai, sesi lain mengubah branch di working directory yang sama dan men-commit file `docs/screenshots/` ke `ui/polish-light-mode`; dokumen ini dibuat di worktree terpisah |
