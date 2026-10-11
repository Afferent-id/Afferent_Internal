# Modul dan folder

Peta tanggung jawab per folder. "Dependensi" berarti apa yang dipanggil modul itu saat runtime.
Ukuran kasar: backend ±16 rb baris Python (`database.py` 3,7 rb baris), dashboard ±390 file terlacak di seluruh repo.

## Root

| Path | Isi |
| --- | --- |
| [docker-compose.yml](../docker-compose.yml) | 10 service (9 aktif + `local_llm` profile `llm`), volume, jaringan `hfl_network` |
| [.env.example](../.env.example) | Template konfigurasi (lihat [SETUP.md](SETUP.md)) |
| [dataset_builder.py](../dataset_builder.py) | Pipeline pembangun dataset deteksi URL (offline) |
| `AFFERENT_deck_full.pptx` | Deck presentasi (biner, 557 KB) |
| [README_SETUP.md](../README_SETUP.md) | Setup lab dari clone baru |
| `Obsidian/` | Vault catatan (±104 MB), **tidak terlacak git** dan tidak ada di `.gitignore` |

## backend/ — API Flask

Entry point: [app.py](../backend/app.py) (membuat app, CORS, gerbang auth deny-by-default, mendaftarkan blueprint).
Dijalankan dengan gunicorn (`gthread`, 1 worker × 16 thread) di [Dockerfile](../backend/Dockerfile).

### Route (lapisan HTTP) — [backend/routes/](../backend/routes/)

| File | Tanggung jawab |
| --- | --- |
| [auth.py](../backend/routes/auth.py) | Login, OTP, session, bahasa akun, ganti password; endpoint lama (Telegram/admin lama) mengembalikan `410` |
| [events.py](../backend/routes/events.py) | Telemetri phishing (redirect-handler, fake login, event, riwayat, profil, eligibility) |
| [incidents.py](../backend/routes/incidents.py) | Tiket insiden dan jejak audit |
| [admin_api.py](../backend/routes/admin_api.py) | Admin: GoPhish (kampanye/template/page), karyawan, divisi, compliance, tren, leaderboard, threat feed/cache, policy |
| [ai_routes.py](../backend/routes/ai_routes.py) | AI behavioral (klasifikasi, laporan, cache, investigasi agentic, generate kampanye) |
| [proxy.py](../backend/routes/proxy.py) | Perangkat proxy, `decision`, verdict, alert (termasuk SSE), traffic, audit, keputusan manual, CA, second opinion |
| [threat.py](../backend/routes/threat.py) | Laporan link, scan URL/file, stats, scan model DL |
| [access_requests.py](../backend/routes/access_requests.py) | Permintaan membuka situs terblokir (berlaku 30 hari) |
| [gamification_routes.py](../backend/gamification_routes.py) | Kuis harian, revive streak, ringkasan laporan, laporan internal |

### Service (logika bisnis) — [backend/services/](../backend/services/)

| File | Tanggung jawab | Bergantung pada |
| --- | --- | --- |
| [auth_service.py](../backend/services/auth_service.py) | Password (argon2), OTP, session, RBAC identity, bootstrap admin | SQLite, `email_service` |
| [email_service.py](../backend/services/email_service.py), [notification_service.py](../backend/services/notification_service.py) | SMTP, outbox tahan-lama, edukasi skor rendah | Mailpit |
| [proxy_service.py](../backend/services/proxy_service.py) | Keputusan allow/block, perangkat, verdict efektif, alert | `proxy_store`, `domain_scanner` |
| [proxy_store.py](../backend/services/proxy_store.py) | Akses PostgreSQL + Redis untuk data plane proxy | psycopg, redis |
| [domain_scanner.py](../backend/services/domain_scanner.py), [ml_service.py](../backend/services/ml_service.py) | Inferensi ML domain-saja, CPU | `models/domain_v3`, sklearn |
| [local_llm_service.py](../backend/services/local_llm_service.py), [hostname_llm_contract.py](../backend/services/hostname_llm_contract.py) | Saran hostname LLM lokal (advisory) | Ollama |
| [threat_service.py](../backend/services/threat_service.py), [report_service.py](../backend/services/report_service.py) | Scan URL/file & laporan SOC | VirusTotal, urlscan ([integrations.py](../backend/integrations.py)) |
| [access_request_service.py](../backend/services/access_request_service.py), [audit_log_service.py](../backend/services/audit_log_service.py) | Access request; daftar kronologis keputusan manusia | SQLite |
| [behavior_service.py](../backend/services/behavior_service.py), [campaign_materials.py](../backend/services/campaign_materials.py), [error_codes.py](../backend/services/error_codes.py) | Heatmap baseline, materi kampanye Mailpit, kode error stabil | — |

### Lainnya di backend/

| File/folder | Tanggung jawab |
| --- | --- |
| [database.py](../backend/database.py) | Skema SQLite (±35 tabel), migrasi, semua query, skor & tier gamifikasi |
| [security.py](../backend/security.py) | `require_roles`, validasi service key, validasi konfigurasi runtime |
| [policy.py](../backend/policy.py) | Matriks keputusan 2D (severity × tier kerentanan pegawai) |
| [gophish_client.py](../backend/gophish_client.py), [integrations.py](../backend/integrations.py) | Klien GoPhish; VirusTotal/urlscan |
| `ai_*.py` | Router LLM multi-provider dengan failover, anonymizer, cache, prompt, agregator data AI |
| [char_bilstm_scanner.py](../backend/char_bilstm_scanner.py), [domain_reputation.py](../backend/domain_reputation.py) | Model Char-BiLSTM dan whitelist reputasi |
| [notification_worker.py](../backend/notification_worker.py), [review_worker.py](../backend/review_worker.py) | Dua proses worker terpisah (service Compose sendiri) |
| `train_domain_model.py`, `evaluate_domain_policy.py`, `seed_*.py` | Pelatihan/evaluasi offline dan seed data demo |
| `models/` | Artefak model terlacak: `domain_v3/` (aktif), `char_bilstm.pt`, `calibrators.pkl`, `production_config.json` |
| `templates/` | Template Jinja lama (dashboard Flask, halaman blokir, kampanye) |
| `quiz_*.py`, `badges.json` | Konten kuis (ID/EN, penjelasan) dan definisi badge |
| `test_*.py` | Tes unittest terisolasi (lihat [SETUP.md](SETUP.md) §5) |

## dashboard/ — Next.js (UI + BFF)

| Path | Tanggung jawab |
| --- | --- |
| [src/proxy.ts](../dashboard/src/proxy.ts) | Middleware Next: cek keberadaan cookie, bypass dev, hook mock |
| `src/app/api/**/route.ts` | BFF: tiap route meneruskan ke Flask lewat [backendClient.ts](../dashboard/src/lib/backendClient.ts) (header `X-Afferent-Session`, timeout 4 dtk) |
| `src/app/` halaman | `/` employee, `/auth`, `/blocked`, `/settings`, `/dashboard/{soc,grc,ciso,phishing-admin}`, `/simulation/education`, `/ai`, `/admin` (redirect ke phishing-admin), `/dev/components` |
| `src/components/admin/` | Seksi workspace staf (incident queue, policy, wizard kampanye, proxy ops, audit log, dll.) |
| `src/components/employee/` | Home pegawai, kuis harian, Spot the Fake, TrainingPicker |
| `src/components/ui/` | Komponen bersama (DataTable, Dialog, Toast, CommandPalette, …) |
| `src/i18n/` | Pesan dan provider bahasa (ID/EN) |
| `src/mocks/` | Mode front-end tanpa backend (`USE_MOCKS=true`), dapat dihapus utuh |
| `src/context/AuthContext.tsx`, `src/hooks/` | State auth, polling, tema, preferensi |
| `scripts/` | Tes BFF/UI berbasis Node (`test-*.cjs`) dan `validate-runtime-env.mjs` |
| [AGENTS.md](../dashboard/AGENTS.md), [CLAUDE.md](../dashboard/CLAUDE.md) | Catatan untuk agen AI: Next.js versi ini punya perubahan breaking, baca `node_modules/next/dist/docs/` |

CSS ada di beberapa file global (`globals.css`, `ui.css`, `dashboard.css`, `workspace.css`, `warmth.css`, …) di samping Tailwind 4.

## proxy/ — penegakan domain

| File | Tanggung jawab |
| --- | --- |
| [tunnel_control.py](../proxy/tunnel_control.py) | Entrypoint container: relay TCP opak di depan Squid, mencabut tunnel aktif per domain |
| [squid.conf](../proxy/squid.conf) | ssl-bump selektif: hanya koneksi yang ditolak di-bump dengan CA lab; sisanya splice |
| [afferent_acl_helper.py](../proxy/afferent_acl_helper.py) | External ACL → memanggil `/api/proxy/decision` |
| [render_error_page.py](../proxy/render_error_page.py), `ERR_AFFERENT_*` | Halaman "BLOCKED BY AFFERENT" offline-safe |

## gophish/ , scripts/ , ml/ , notebooks/ , dataset/ , archive/

| Folder | Isi |
| --- | --- |
| [gophish/](../gophish/) | Dockerfile dan `config.json` (+ contoh) untuk GoPhish |
| [scripts/](../scripts/) | [setup_lab.py](../scripts/setup_lab.py) (bootstrap ENV + PKI, stdlib saja), [check_submission.cjs](../scripts/check_submission.cjs) (guard rahasia/jalur terlarang) |
| [ml/local_llm/](../ml/local_llm/) | Persiapan data, fine-tune, evaluasi, dan Modelfile untuk LLM hostname lokal (eksperimen; belum lolos gerbang promosi) |
| [notebooks/](../notebooks/) | Notebook pelatihan v3/v4 |
| `dataset/` | Dataset latih/olahan (±113 MB terlacak) |
| [archive/](../archive/README.md) | Rencana lama dan integrasi yang dipensiunkan (n8n, Telegram); bukan bagian demo aktif |
| [docs/](.) | Runbook dan bukti evaluasi (lihat daftar di [README](../README.md)) |

`TODO: konfirmasi ke tim`: pemilik tiap modul (tidak tercatat di repo; tidak ada CODEOWNERS).
