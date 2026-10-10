# Afferent — Product Requirements Document (PRD)

| Item | Nilai |
| --- | --- |
| Produk | Afferent (internal cybersecurity product, human-centric telemetry security) |
| Dokumen | PRD v0.1 (draft untuk review tim & mentor) |
| Branch | `docs/prd-srs-internal` |
| Dokumen pendamping | [SRS.md](SRS.md) |
| Status kode | Lab/demo untuk 5–8 user. Bukan klaim production-ready atau sertifikasi regulasi (lihat [README.md](../README.md)) |

**Konvensi status.** Setiap kapabilitas di dokumen ini diberi salah satu label:

- **[Existing]** — ada di kode repo ini dan sudah ditelusuri ke modul/file-nya (rujukan lengkap ada di SRS).
- **[Partial]** — sebagian ada di kode; celahnya disebutkan eksplisit.
- **[Future]** — hanya rencana/masukan; tidak ada kode. Semua ini dikumpulkan di bagian 9 (*Future Work*).

Dokumen ini tidak memuat kredensial atau data pribadi. Contoh email/akun yang ada di seed data repo sengaja tidak dikutip.

---

## 1. Ringkasan & Problem Statement

### 1.1 Ringkasan

Afferent adalah platform keamanan siber internal yang menggabungkan dua sisi dalam satu dashboard:

1. **Sisi manusia** — simulasi phishing (GoPhish), edukasi, gamifikasi (poin, badge, streak, quiz harian), pelaporan link/file mencurigakan oleh karyawan, dan peringatan edukasi bagi karyawan dengan skor rendah.
2. **Sisi jaringan** — *centralized forward proxy* (Squid + TCP relay) dengan **domain gate**: tiap koneksi karyawan diputuskan allow/block berdasarkan kebijakan manual SOC dan model ML domain-only, dengan telemetri real-time (SSE) dan audit append-only.

Keduanya diakses lewat dashboard berbasis role (employee, phishing admin, SOC, GRC, CISO) dengan login email + password + OTP.

### 1.2 Problem statement

| # | Masalah | Dampak |
| --- | --- | --- |
| P1 | Awareness phishing biasanya diukur sekali setahun lewat training formal, tanpa telemetri perilaku nyata. | Organisasi tidak tahu siapa/divisi mana yang paling berisiko. |
| P2 | SOC tidak punya satu tampilan yang menghubungkan *perilaku karyawan* (klik, laporan) dengan *lalu lintas web* (domain yang diakses). | Respons insiden lambat dan terfragmentasi. |
| P3 | GRC/CISO sulit membuktikan kesiapan kontrol (ISO 27001:2022, UU PDP No. 27/2022) dengan data, bukan asumsi. | Laporan kepatuhan bersifat naratif. |
| P4 | Keputusan blokir/izinkan domain jarang punya jejak audit yang tidak bisa diubah. | Akuntabilitas lemah saat ada sengketa atau audit. |

### 1.3 Tujuan produk

- Mengukur dan menaikkan *human security posture* dengan data (skor, tier, tren mingguan).
- Memberi SOC kendali yang dapat diaudit atas akses domain tanpa mendekripsi HTTPS yang diizinkan.
- Memberi GRC/CISO bukti kesiapan kontrol yang dihitung dari telemetri nyata, dengan rumus yang transparan.

### 1.4 Bukan tujuan (non-goals)

- Bukan SIEM, EDR, atau NAC. Bukan pengganti firewall perimeter.
- Bukan inspeksi konten HTTPS (allowed HTTPS di-*splice*, tidak didekripsi).
- Bukan klaim sertifikasi ISO 27001 / kepatuhan UU PDP; hanya *readiness mapping* berbasis telemetri.

---

## 2. Target User

| Segmen | Siapa | Kebutuhan utama |
| --- | --- | --- |
| Karyawan (end user) | Seluruh karyawan perusahaan, perangkat dikelola perusahaan | Belajar dengan cara ringan, melaporkan hal mencurigakan, mengecek link/file dengan aman |
| Tim keamanan operasional | Analis SOC | Antrian insiden, traffic proxy real-time, kontrol Block/Allow, advice AI |
| Tim program awareness | Phishing administrator / security awareness | Meluncurkan kampanye, mengelola roster karyawan & divisi |
| Tim tata kelola | GRC | Readiness kepatuhan, ambang batas, inbox persetujuan, audit |
| Eksekutif keamanan | CISO | Ringkasan eksekutif, tren, risiko per divisi |

Skala saat ini: **5–8 user lab** ([README.md](../README.md)). Target skala perusahaan belum diuji (lihat NFR skalabilitas di SRS dan Open Questions).

---

## 3. Role dan Jobdesk

Keputusan role: **5 role**, karena kode mendefinisikan `VALID_ROLES = {employee, phishing_admin, soc, grc, ciso}` ([auth_service.py](../backend/services/auth_service.py)), dan constraint database `employee_accounts.role` membatasi nilai yang sama ([database.py](../backend/database.py)). Pilihan "SOC + Admin saja" tidak sesuai dengan kode yang ada; lihat Open Question OQ-01 jika tim ingin menyederhanakan.

> Catatan penamaan: identifier RBAC di kode adalah `phishing_admin`, sedangkan di UI diberi label **Administrator** (dipertahankan agar RBAC tidak berubah — [TECHNICAL_DEBT_CHECKLIST.md](TECHNICAL_DEBT_CHECKLIST.md)).

RBAC ditegakkan di server lewat `require_roles(...)` ([security.py](../backend/security.py)); role tidak pernah dibaca dari header/body klien.

### 3.1 Employee

**Jobdesk:** menjalankan aktivitas awareness harian dan menjadi sensor manusia.

- Mengerjakan quiz harian, *Spot the Fake*, dan training; mengumpulkan poin/badge/streak. **[Existing]**
- Scan URL, melaporkan link mencurigakan (masuk ke inbox SOC/GRC), dan scan file privat (hasil hanya terlihat employee). **[Existing]**
- Mendaftarkan perangkat ke proxy dan mengonfigurasi proxy OS/browser; meminta akses domain yang diblokir (*access request*). **[Existing]**

### 3.2 Phishing Administrator ("Administrator")

**Jobdesk:** mengelola program simulasi dan data karyawan.

- Membuat/mengubah akun (employee, SOC, GRC, CISO) dan divisi. **[Existing]**
- Membuat template email & landing page, meluncurkan, menyelesaikan, dan menghapus kampanye GoPhish; memilih penerima hanya dari employee aktif. **[Existing]**
- Melihat leaderboard dan login history. **[Existing]**

### 3.3 SOC (Security Operations Center)

**Jobdesk:** deteksi, triase, dan respons.

- Memantau antrian insiden, assign/resolve/reopen tiket dengan audit trail. **[Existing]**
- Memantau traffic proxy real-time (SSE), memutuskan Block/Allow domain secara manual dengan alasan; semua keputusan tercatat append-only. **[Existing]**
- Memutuskan *access request* employee; menyetujui warning edukasi; meminta *second opinion* domain dari local LLM (opsional, advisory). **[Existing]**

### 3.4 GRC (Governance, Risk, Compliance)

**Jobdesk:** memastikan kontrol terukur dan dapat dibuktikan.

- Memantau *compliance readiness* (ISO 27001:2022 A.6.3, A.6.8, A.8.12; UU PDP Pasal 35 dan 46) dan mengubah ambang target. **[Existing]**
- Meninjau inbox keamanan (laporan link, employee di bawah baseline), menyetujui warning, membaca audit log. **[Existing]**

### 3.5 CISO

**Jobdesk:** pengambilan keputusan eksekutif.

- Melihat ringkasan eksekutif, tren mingguan, readiness, kampanye, dan audit (read-mostly; tidak dapat resolve insiden). **[Existing]**
- Ekspor laporan eksekutif PDF dari halaman AI Intelligence. **[Existing]**

### 3.6 Matriks akses ringkas

| Kapabilitas | Employee | Admin | SOC | GRC | CISO |
| --- | :-: | :-: | :-: | :-: | :-: |
| Quiz, gamifikasi, scan URL/file, report link | ✔ | | | | |
| Registrasi perangkat proxy | ✔ | | | | |
| Kelola akun, divisi, kampanye | | ✔ | | | |
| Melihat kampanye | | ✔ | | | ✔ |
| Block/Allow domain, resolve insiden | | | ✔ | | |
| Traffic/alert/audit proxy (baca) | | | ✔ | | ✔ |
| Inbox keamanan | | | ✔ | ✔ | |
| Edit ambang readiness | | | | ✔ | |
| Compliance summary (baca) | | | | ✔ | ✔ |
| Audit log gabungan | | | ✔ | ✔ | ✔ |

Sumber: dekorator `require_roles` di `backend/routes/*.py`. Detail per endpoint ada di SRS §8.

---

## 4. User Stories dan Acceptance Criteria

Format: *Sebagai <role>, saya ingin <tujuan> agar <manfaat>.* Setiap AC diverifikasi terhadap perilaku kode; ID FR merujuk ke SRS.

### Autentikasi & akun

**US-01 — Login aman.** Sebagai user, saya ingin login dengan email, password, dan OTP agar akun saya terlindungi. *(FR-001–FR-004)* **[Existing]**
- AC1: Login memerlukan password valid lalu OTP yang dikirim lewat email (Mailpit di lab).
- AC2: OTP kedaluwarsa setelah 300 detik (default), maksimum 5 percobaan, cooldown resend 60 detik, dan batas 5 permintaan per 900 detik.
- AC3: Session berupa cookie HTTP-only dengan TTL default 86400 detik; setelah itu user harus login ulang.
- AC4: Password disimpan dengan hash Argon2; ganti password mencabut semua session.

**US-02 — Kelola akun.** Sebagai Administrator, saya ingin membuat dan menonaktifkan akun beserta role dan divisinya agar akses sesuai tugas. *(FR-005)* **[Existing]**
- AC1: Role hanya boleh salah satu dari 5 role valid; nilai lain ditolak.
- AC2: Akun nonaktif tidak dapat login dan tidak menerima kampanye.

### Phishing simulation

**US-03 — Meluncurkan kampanye.** Sebagai Administrator, saya ingin meluncurkan simulasi phishing ke employee terpilih agar perilaku nyata terukur. *(FR-010–FR-013)* **[Existing]**
- AC1: Penerima hanya employee aktif yang dipilih (bukan admin/SOC).
- AC2: Kampanye berjalan lewat API GoPhish nyata; kegagalan API ditampilkan, bukan dipalsukan.
- AC3: Klik/submit tercatat sebagai event dengan deduplikasi; employee yang submit diarahkan ke halaman edukasi dan skor hanya dihitung sekali.
- AC4: Tidak ada kredensial asli yang ditangkap pada form demo.

### Employee awareness

**US-04 — Belajar harian.** Sebagai employee, saya ingin quiz harian dan skor agar termotivasi menjaga kewaspadaan. *(FR-020–FR-022)* **[Existing]**
- AC1: Quiz harian dapat diselesaikan sekali per hari dan menambah streak.
- AC2: Reward harian dibatasi (daily cap) dan laporan duplikat tidak menambah poin.

**US-05 — Melaporkan hal mencurigakan.** Sebagai employee, saya ingin melaporkan link agar SOC dapat menindaklanjuti. *(FR-023–FR-025)* **[Existing]**
- AC1: Laporan dievaluasi dengan VirusTotal dan urlscan; kegagalan provider atau kuota ditampilkan sebagai *Unknown*, bukan *safe*.
- AC2: Batas 20 permintaan per jam per akun.
- AC3: Hanya laporan link yang masuk ke inbox SOC/GRC; scan file privat tidak membuat laporan SOC maupun skor.

**US-06 — Scan file privat.** Sebagai employee, saya ingin memeriksa file yang saya terima tanpa file itu dibagikan ke SOC. *(FR-026)* **[Existing]**
- AC1: Ukuran maksimum 1–10 MB (default 10), memerlukan persetujuan upload.
- AC2: Byte asli dihapus secara logis setelah selesai atau kedaluwarsa (default 3600 detik).

### Proxy / domain gate

**US-07 — Menghubungkan perangkat.** Sebagai employee, saya ingin mendaftarkan perangkat agar traffic saya dinilai oleh domain gate. *(FR-030–FR-031)* **[Existing]**
- AC1: Dashboard menampilkan status *Terhubung* hanya setelah Squid menjawab probe koneksi.
- AC2: Otorisasi perangkat mengikuti TTL (default 86400 detik) dan diperbarui lewat heartbeat.

**US-08 — Domain gate deterministik.** Sebagai SOC, saya ingin keputusan domain mengikuti urutan prioritas yang jelas agar hasilnya dapat diprediksi. *(FR-032–FR-035)* **[Existing]**
- AC1: Urutan: Block manual SOC → Allow manual SOC → verdict ML konklusif → ML *Unknown* (diizinkan untuk review) → inferensi pending/timeout/error (ditolak sementara, tidak disimpan sebagai blacklist).
- AC2: Block manual selalu mengalahkan ML dan Allow lama.
- AC3: Jika Decision API mati, default `PROXY_FAIL_MODE=closed` (tidak bypass inspeksi).
- AC4: Perubahan kebijakan mencabut tunnel yang sebelumnya diizinkan dalam interval revocation (default 0,5 detik + latensi API).

**US-09 — Kontrol dan audit SOC.** Sebagai SOC, saya ingin Block/Allow dengan alasan dan jejak audit permanen agar akuntabel. *(FR-036–FR-038)* **[Existing]**
- AC1: Setiap keputusan mencatat aktor, role, waktu, alasan, state sebelum/sesudah, request ID, domain, dan alert sumber.
- AC2: Trigger database menolak `UPDATE` dan `DELETE` pada tabel audit.
- AC3: Alert baru muncul di dashboard SOC lewat SSE tanpa reload.

**US-10 — Block page.** Sebagai employee, saya ingin tahu mengapa domain diblokir dan bisa meminta akses. *(FR-039–FR-040)* **[Existing]**
- AC1: Koneksi yang ditolak menampilkan halaman *BLOCKED BY AFFERENT* (HTTPS memerlukan CA lab terpasang).
- AC2: Employee dapat mengirim access request; SOC memutuskan allow/deny dengan catatan.

### Insiden & AI

**US-11 — Menangani insiden.** Sebagai SOC, saya ingin menugaskan dan menyelesaikan tiket dengan jejak audit. *(FR-040–FR-042)* **[Existing]**
- AC1: Event `assigned`, `unassigned`, `resolved`, `reopened` tercatat dengan aktor dan catatan.
- AC2: Insiden severity tinggi mengirim email ke analis SOC aktif (dapat dimatikan).

**US-12 — Advice AI yang aman.** Sebagai SOC, saya ingin second opinion untuk hostname mencurigakan tanpa risiko auto-block. *(FR-043)* **[Existing]**
- AC1: Local LLM opsional (profil Compose `llm`), tanpa fallback cloud dan tanpa port publik.
- AC2: Output bersifat advisory; tidak dapat menulis kebijakan enforcement.

### Kepatuhan & pelaporan

**US-13 — Readiness kepatuhan.** Sebagai GRC, saya ingin skor kesiapan per klausul beserta bukti dan rumusnya. *(FR-050–FR-052)* **[Existing]**
- AC1: Tiap klausul menampilkan evidence (data dan rumus yang dipakai).
- AC2: GRC dapat mengubah target; CISO hanya membaca. Klausul UU PDP Pasal 46 (72 jam) ditandai *legally mandated* dan targetnya tetap.

**US-14 — Ringkasan eksekutif.** Sebagai CISO, saya ingin ringkasan dan tren mingguan agar dapat melaporkan ke manajemen. *(FR-053–FR-055)* **[Existing]**
- AC1: Tren mingguan (rata-rata skor, high-risk, insiden terbuka, laporan, klik) dari snapshot per Senin UTC.
- AC2: Laporan eksekutif dapat diekspor ke PDF.

**US-15 — Peringatan edukasi.** Sebagai SOC/GRC, saya ingin menyetujui email edukasi bagi karyawan berskor rendah. *(FR-056)* **[Existing]**
- AC1: Hanya employee aktif dengan skor `< 60` (dari 200, dapat dikonfigurasi) yang memenuhi syarat; dicek ulang sebelum kirim.
- AC2: Default manual (butuh persetujuan); mode otomatis opsional; cooldown 24 jam; retry persisten tanpa duplikat.

### Masukan mentor (belum ada di kode — lihat §7 dan §9)

**US-16 — Laporan per user/divisi/company.** Sebagai CISO, saya ingin satu mekanisme pelaporan konsisten di tiga tingkat. **[Partial]**
- AC1 (target): Satu skema laporan dengan filter `scope = user | division | company`, periode, dan ekspor (PDF/CSV).
- AC2 (kondisi kini): data per user (`/api/ai/user/<email>`, reports-summary), per divisi (leaderboard/rata-rata divisi, incident `divisi`), dan company-wide (compliance-summary, trends) sudah ada tetapi tersebar dan belum satu skema/ekspor seragam.

**US-17 — Sinkronisasi identitas.** Sebagai Administrator, saya ingin akun dan divisi tersinkron dari AD/Entra agar tidak input manual. **[Future]**
- AC (target): provisioning/deprovisioning otomatis; role dipetakan dari grup direktori. Tidak ada kode saat ini.

**US-18 — SLA kepatuhan.** Sebagai GRC, saya ingin target waktu respons/penutupan yang diukur dan dilaporkan. **[Partial]**
- AC (kondisi kini): MTTC (rata-rata jam ke penutupan insiden) dan target 72 jam UU PDP Pasal 46 sudah dihitung/tersimpan. Belum ada SLA per severity, timer, atau notifikasi pelanggaran.

**US-19 — White-label branding.** Sebagai pemilik produk, saya ingin logo/nama/warna dapat dikonfigurasi per organisasi. **[Future]**
- AC (target): tema dan nama produk dari konfigurasi, bukan hardcode. Saat ini nama "Afferent" dan logo ditanam di kode/asset.

---

## 5. Scope

### 5.1 In scope — rilis lab saat ini [Existing]

| Area | Isi |
| --- | --- |
| Identitas & akses | Email/password + OTP, session cookie, 5 role RBAC, ganti password, bahasa EN/ID per akun |
| Simulation | GoPhish: template, landing page, kampanye, sinkronisasi telemetri, halaman edukasi |
| Awareness | Quiz harian, Spot the Fake, gamifikasi (poin, badge, streak, leaderboard), scan URL/file, report link |
| Domain gate | Squid + TCP relay, Decision API, Redis hot path, PostgreSQL source of truth, ML domain-only lokal, SSE ke SOC, revocation, block page, access request |
| Operasi SOC | Antrian insiden, threat cache/IoC, audit gabungan, login history, local LLM advisory opsional |
| GRC/Eksekutif | Compliance readiness ISO 27001/UU PDP, ambang konfigurabel, ringkasan eksekutif, tren mingguan, ekspor PDF |
| Platform | Docker Compose (10 service termasuk worker dan LLM opsional), Mailpit sebagai SMTP lab |

### 5.2 Out of scope

- Integrasi SMTP eksternal (saat ini Mailpit saja) dan sensor/NAC baru — dinyatakan Future Work ([README.md](../README.md)).
- Dekripsi HTTPS untuk inspeksi konten; klaim zero false positive; sertifikasi regulasi.
- Pemakaian VirusTotal/urlscan di jalur hot path proxy (sengaja dipisah dari proxy ML).
- Integrasi n8n/Telegram (sudah di-retire ke `archive/`).

### 5.3 Future Work (tidak ada di kode)

Lihat §9.

---

## 6. Prioritas (MoSCoW)

"Scale of priority" dari mentor diwujudkan sebagai MoSCoW di bawah dan harus ditinjau mentor (OQ-05).

| Prioritas | Item | Status |
| --- | --- | --- |
| **Must** | Login + OTP + RBAC server-side | Existing |
| **Must** | Domain gate dengan urutan keputusan deterministik dan fail-closed | Existing |
| **Must** | Audit append-only atas keputusan SOC | Existing |
| **Must** | Telemetri simulasi phishing dan skor per employee | Existing |
| **Must** | Batas lingkup dan kebijakan perangkat (BYOD) yang jelas | Future (kebijakan/dok) — lihat §7 |
| **Should** | Compliance readiness ISO/UU PDP dengan evidence | Existing |
| **Should** | Pelaporan seragam per user/divisi/company | Partial |
| **Should** | SLA kepatuhan terukur (per severity, timer, pelanggaran) | Partial |
| **Should** | Integrasi AD/Entra (provisioning dan SSO) | Future |
| **Could** | White-label branding | Future |
| **Could** | Local LLM advisory, AI heatmap | Existing (opsional) |
| **Could** | Ekspor CSV/PDF seragam | Partial |
| **Won't (rilis ini)** | Ekspor log ke SIEM, VPN enforcement, deteksi NAC | Future |

---

## 7. Masukan Mentor sebagai Requirement

| ID | Masukan mentor | Requirement | Status kode | Rujukan SRS |
| --- | --- | --- | --- | --- |
| MR-01 | **BYOD dan ruang lingkup jelas** | Produk hanya menjamin pengawasan pada perangkat yang terdaftar dan diproksi. Perangkat pribadi (BYOD) wajib punya kebijakan: persetujuan tertulis (consent), pemasangan CA lab terbatas, dan batas data yang dikumpulkan (hanya domain/CONNECT authority, bukan path/cookie/konten). | Perilaku teknis ada (device binding, domain-only, tidak ada payload); **kebijakan BYOD formal belum ada**. [Partial] | SRS §10 |
| MR-02 | **Scale of priority** | Setiap requirement punya prioritas (MoSCoW) dan setiap alert/insiden punya urutan severity. | MoSCoW ada di §6; severity insiden (`low…high`) dan urgensi alert (`Critical/Unknown`) ada. [Partial] | SRS §3 (kolom Prioritas) |
| MR-03 | **SLA untuk compliance** | Target waktu terdefinisi dan terukur, minimal: notifikasi pelanggaran data ≤ 72 jam (UU PDP Pasal 46) dan MTTC insiden. | MTTC dan ambang 72 jam ada; timer/eskalasi SLA belum. [Partial] | FR-052, NFR-C |
| MR-04 | **White label branding** | Nama, logo, warna, dan domain email dapat dikonfigurasi per organisasi tanpa ubah kode. | Tidak ada. [Future] | FR-F04 |
| MR-05 | **Integrasi AD** | Sinkronisasi user/grup dari Active Directory / Entra ID untuk provisioning dan pemetaan role. | Tidak ada. [Future] | FR-F01 |
| MR-06 | **Mekanisme reporting per user / divisi / company** | Satu mekanisme dengan tiga scope dan ekspor. | Komponen tersebar sudah ada. [Partial] | FR-054, FR-F05 |
| MR-07 | **Alasan ilmiah pemilihan tech stack** | Setiap komponen stack punya justifikasi teknis. | Didokumentasikan. [Done] | SRS §9 |

---

## 8. Metrik Keberhasilan

Baseline lab: 5–8 user, jadi target dibawah adalah **usulan**, bukan hasil terukur. Nilai yang sudah ada di repo dicatat sebagai baseline.

| Kategori | Metrik | Sumber data di kode | Target usulan | Baseline terukur di repo |
| --- | --- | --- | --- | --- |
| Perilaku | Click rate simulasi phishing | `events` (tabel), kampanye GoPhish | Turun tiap kuartal | Belum ada data produksi |
| Perilaku | Report rate (report-to-click) | `threat_reports`, `events` | ≥ 70% (default ambang ISO A.6.8) | Ambang default 70% |
| Awareness | Training completion | `user_history.viewed_training_count` | ≥ 85% (default ambang ISO A.6.3) | Ambang default 85% |
| Awareness | Employee di bawah baseline skor | `user_history.points` | < 10% populasi | Ambang edukasi: skor < 60/200 |
| Respons | MTTC insiden | `get_compliance_summary` | Sesuai SLA yang disepakati (OQ-04) | Dihitung otomatis |
| Respons | Notifikasi pelanggaran data | Readiness UU PDP Pasal 46 | ≤ 72 jam | Ambang 72 jam (statutory) |
| Proxy | Latensi keputusan domain | `PROXY_DECISION_TIMEOUT_SECONDS` | p95 < 2,5 s (batas timeout) | Timeout 2,5 s; p95 belum diukur |
| Proxy | Waktu revocation setelah Block | `PROXY_REVOCATION_INTERVAL_SECONDS` | ≤ 1 s + latensi API | Interval 0,5 s |
| ML | Presisi blok domain; recall keseluruhan | [DOMAIN_ML_EVALUATION.md](DOMAIN_ML_EVALUATION.md) | Naikkan recall | Recall keseluruhan v3 21,18%; OOD judol 0/70 blok (jujur: belum memadai) |
| Audit | Keputusan SOC yang punya audit lengkap | `proxy_decision_audit` | 100% | Dijamin trigger DB |
| Adopsi | Perangkat terhubung / employee aktif | `proxy_devices` | ≥ 90% | Belum diukur |

---

## 9. Future Work (bukan fitur yang sudah ada)

Hasil pemeriksaan kode (grep Entra/AD/LDAP/SAML/SSO/SIEM/VPN/BYOD/white-label/tenant/SLA di `backend/`, `dashboard/src/`, `proxy/`, `docker-compose.yml`) tidak menemukan implementasi untuk butir berikut. Kemunculan kata "SSO"/"VPN" di repo hanya pada materi simulasi/quiz dan data mock UI, bukan integrasi.

| ID | Item | Catatan |
| --- | --- | --- |
| FW-01 | Integrasi Active Directory / Entra ID (provisioning, SSO, pemetaan grup→role) | Akun saat ini lokal (`employee_accounts`), dibuat manual oleh Administrator |
| FW-02 | VPN enforcement / pengecekan posture jaringan | Kolom `vpn` di UI login-history adalah data mock/placeholder; backend menyatakan network "Not collected" |
| FW-03 | Parsing log ke SIEM / ekspor event (CEF/syslog) | Tidak ada konektor; telemetri hanya di PostgreSQL/SQLite dan SSE internal |
| FW-04 | SMTP eksternal produksi | Saat ini Mailpit; dinyatakan Future Work di README |
| FW-05 | Sensor / NAC baru | Dinyatakan Future Work di README |
| FW-06 | White-label branding (konfigurasi tema, nama, logo) | Branding tertanam di kode dan `dashboard/public/` |
| FW-07 | Multi-tenant (beberapa perusahaan dalam satu instalasi) | Tidak ada kolom tenant; satu organisasi per instalasi |
| FW-08 | SLA engine (timer per severity, eskalasi, laporan pelanggaran) | Hanya MTTC dan ambang statis |
| FW-09 | Laporan terpadu per user/divisi/company dengan ekspor seragam | Komponen tersebar sudah ada |
| FW-10 | Kebijakan BYOD formal dan alur consent di aplikasi | Hanya anjuran di dokumen runbook |
| FW-11 | Manajemen perangkat (MDM) / distribusi CA otomatis | CA dipasang manual |
| FW-12 | Pengerasan untuk skala perusahaan (HA, SQLite→PostgreSQL penuh, beban uji) | Lab 5–8 user |

---

## 10. Asumsi dan Risiko

### 10.1 Asumsi

| ID | Asumsi |
| --- | --- |
| A1 | Perusahaan memiliki atau dapat mewajibkan konfigurasi proxy pada perangkat yang diawasi. |
| A2 | Karyawan memberi persetujuan (consent) atas pemantauan domain dan pemasangan CA lab pada perangkat uji. |
| A3 | Satu instalasi melayani satu organisasi. |
| A4 | Server dijangkau lewat jaringan privat (LAN/Tailscale); port 3128/3000/5000 tidak dibuka ke Internet. |
| A5 | Kunci API VirusTotal/urlscan tersedia; tanpa itu hasil scan berstatus *Unknown*. |
| A6 | Waktu bisnis mengikuti WIB untuk perhitungan harian reward. |

### 10.2 Risiko

| ID | Risiko | Dampak | Mitigasi / status |
| --- | --- | --- | --- |
| R1 | Recall model domain rendah (21,18% keseluruhan; kategori judol/adult belum terverifikasi) | Domain berbahaya lolos | Dinyatakan jujur di dokumen; SOC manual override; dataset terverifikasi dibutuhkan |
| R2 | Pemantauan perangkat pribadi menimbulkan isu privasi/hukum (UU PDP) | Penolakan karyawan, risiko hukum | Batasi ke domain-only; kebijakan BYOD & consent (MR-01); DPO review (OQ-03) |
| R3 | Proxy device-wide: banyak user/aplikasi pada satu perangkat berbagi sumber IP | Atribusi salah | Dicatat di dokumen; pakai perangkat terpisah per user |
| R4 | Aplikasi certificate-pinned menolak halaman blok HTTPS | Pengalaman user buruk | Didokumentasikan sebagai batas ([SELECTIVE_TLS_DEMO.md](SELECTIVE_TLS_DEMO.md)) |
| R5 | Kredensial historis pernah ter-commit di riwayat Git | Kebocoran kunci | Rotasi kunci (lihat [FINAL_SUBMISSION.md](FINAL_SUBMISSION.md), [API_CREDENTIAL_LIFECYCLE.md](API_CREDENTIAL_LIFECYCLE.md)); tidak ada rewrite history |
| R6 | Kuota VirusTotal (default 4 req/menit) membatasi throughput scan | Antrian scan lambat | Rate limit terpusat, status provider ditampilkan jujur |
| R7 | SQLite sebagai penyimpanan akun/phishing | Batas konkurensi dan skala | Ditandai sebagai pengerasan skala (FW-12) |
| R8 | Ketergantungan pada GoPhish (proyek eksternal) | Perubahan API / keamanan | API key terpisah, TLS terverifikasi, CA bundle wajib |
| R9 | Ekspektasi mentor (AD, SLA, white label) belum terpenuhi di kode | Gap saat evaluasi | Ditandai eksplisit [Future]/[Partial] di dokumen ini |
| R10 | Klaim kepatuhan berlebihan | Reputasi/hukum | Readiness ≠ sertifikasi; teks produk menyatakannya |

---

## 11. Open Questions

Hal yang **tidak dapat disimpulkan dari kode** dan perlu keputusan tim/mentor.

| ID | Pertanyaan | Pemilik | Mengapa penting |
| --- | --- | --- | --- |
| OQ-01 | Role final: tetap 5 role (employee, Administrator, SOC, GRC, CISO) atau disederhanakan menjadi SOC + Admin? Placeholder di brief belum terisi; dokumen ini mengikuti kode (5 role). | Product owner | Mengubah matriks akses, UI, dan constraint DB |
| OQ-02 | Siapa target pelanggan: satu perusahaan internal atau multi-tenant/white-label untuk banyak klien? | Product owner + mentor | Menentukan FW-06/FW-07 dan arsitektur data |
| OQ-03 | Kebijakan BYOD yang disetujui Legal/DPO: apakah perangkat pribadi diizinkan, dan bentuk consent-nya? | Legal/DPO | Syarat kepatuhan UU PDP dan penerimaan karyawan |
| OQ-04 | Angka SLA konkret (waktu respons/penutupan per severity, eskalasi) untuk compliance. | GRC + mentor | Hanya 72 jam UU PDP dan MTTC yang ada |
| OQ-05 | Definisi "scale of priority" mentor: MoSCoW, skala severity, atau skor risiko berbobot? | Mentor | Menentukan skema prioritas requirement/insiden |
| OQ-06 | Sumber identitas target: Active Directory on-prem, Entra ID, atau keduanya? Perlu SSO atau hanya provisioning? Mode sinkronisasi dan pemetaan role? | IT/Infra | Menentukan desain FW-01 |
| OQ-07 | Target skala (jumlah karyawan, perangkat, RPS proxy) dan ketersediaan (SLO uptime). | Product owner + Infra | Menentukan NFR dan kebutuhan HA |
| OQ-08 | Retensi data: berapa lama traffic, audit, dan telemetri disimpan? (variabel `PROXY_TRAFFIC_RETENTION_DAYS`/`PROXY_AUDIT_RETENTION_DAYS` ada, nilai kebijakan belum diputuskan) | Legal/GRC | Kepatuhan dan biaya penyimpanan |
| OQ-09 | Apakah ada kebutuhan ekspor ke SIEM, dan SIEM apa? | SOC | Menentukan format event (FW-03) |
| OQ-10 | Format dan audiens laporan per user / divisi / company: siapa melihat apa, periode, privasi data per user? | CISO + HR | Menentukan FW-09 dan batas akses |
| OQ-11 | Sumber dan lisensi dataset training; siapa yang menyediakan dataset kategori judol/adult yang terverifikasi? | Tim ML | Menentukan perbaikan recall (R1) |
| OQ-12 | Strategi distribusi CA lab ke perangkat karyawan (manual, MDM, GPO)? | IT/Infra | Syarat block page HTTPS |
| OQ-13 | Nama produk dan identitas visual final (untuk white-label); apakah "Afferent" nama final? | Product owner | Cakupan branding |
| OQ-14 | Apakah ambang readiness default (berbasis benchmark industri) disetujui GRC, dan siapa yang mengkalibrasi per sektor? | GRC | Validitas skor kepatuhan |
