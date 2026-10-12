# Rencana perapian repo

Disusun 11 Oktober 2026 dari audit baca-saja. **Belum ada perintah di dokumen ini yang dijalankan.**
Semua langkah di bawah menunggu persetujuan manusia. Tidak ada push, hapus, rename, atau perubahan
pengaturan repo selama audit.

## 0. Status 12 Oktober 2026 (sudah dijalankan atas persetujuan pemilik)

- `main` digabung ke `development` (merge), lalu `main` dihapus dari remote. Tag arsip `archive/main-20261011` (22caebd).
- Default branch repo: `development`. Branch baru `staging` dan `prod` (sama dengan `development`, tanpa proteksi).
- `ui/leaderboard-flat` dihapus (tag `archive/ui-leaderboard-flat`). `external` dihapus dari remote; cadangan lokal
  `external-branch-343eea8.bundle` di folder backup. `aria-dev` dan `feature/vps-deployment` tetap ada
  (commit unik vps disimpan di tag `archive/feature-vps-deployment`).
- Repo sekarang bernama `Afferent-id/Afferent_Internal` (sebelumnya `Llovind/Human_Firewall`).
- Branch protection gagal dipasang (HTTP 403: butuh GitHub Pro atau repo public). Diputuskan 12 Oktober: tanpa proteksi; aturan PR hanya kesepakatan tim.
- Di bagian bawah, `main` berarti `prod` dan proteksi hanya direncanakan untuk `prod`.
- Daftar branch di tabel bagian 1 adalah keadaan saat audit, bukan keadaan sekarang.

## 1. Keadaan saat ini (saat audit)

| Branch remote | Tip | Penulis terakhir | Tanggal | Merged ke development | Merged ke main | Di belakang / di depan development | PR terbuka | Klasifikasi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `development` | f88b640 | Farrel Ardya | 2026-10-07 | - | tidak (16 di depan, 3 di belakang main) | - | tidak ada | aktif |
| `main` | 22caebd | dapa | 2026-10-11 | tidak (3 commit pemangkasan belum ada di development) | - | 3 / 16 (dibanding main) | tidak ada | aktif, default branch |
| `ui/leaderboard-flat` | 2951031 | Llovind | 2026-10-02 | ya | ya | 22 / 0 | tidak ada | sudah ter-merge |
| `feature/vps-deployment` | 10e7151 | flyingsundaman | 2026-08-28 | tidak | tidak | 73 / 5 | tidak ada | basi (44 hari) |
| `aria-dev` | 6bb14fd | dapa | 2026-10-03 | (dikecualikan) | (dikecualikan) | - | - | dicatat saja |
| `external` | 343eea8 | joshsoeros | 2026-10-11 | (dikecualikan) | (dikecualikan) | - | - | dicatat saja |

PR: `gh` login sebagai `arelardya` dengan izin WRITE; `gh pr list --state all` mengembalikan daftar kosong.

Catatan `external` (tidak disentuh): branch ini masih membawa 9 blob di atas 10 MiB dan ±100 commit riwayat lama.
Inilah sebab clone mirror ukurannya 288 MiB, bukan 10,8 MiB seperti di `docs/REPOSITORY_SIZE.md` (di `main`).
Selama `external` ada di remote, ukuran clone penuh tidak turun. Pemiliknya perlu memindahkannya (atau
rebase ke riwayat baru) sebelum klaim ukuran itu benar untuk semua orang.

## 2. development vs main

- `main` lebih baru (2026-10-11 vs 2026-10-07), tetapi hanya 3 commit yang tidak ada di `development`:
  `938eeca` (pemangkasan data), `cc95a87` (refactor `ai_cache`, `ai_anonymizer`, `behavior_service` + `test_clean_code.py`),
  `22caebd` (dokumen migrasi).
- `development` punya 16 commit yang tidak ada di `main`: seluruh pekerjaan UI/backend Farrel 5-7 Oktober
  (137 file, +11263/-6731 baris). Diff pohon `main` vs `development` per folder: `dashboard/` 109 file berubah
  (semuanya hanya di development), `backend/` 30 file, `docs/` 2 file, `proxy/` dan `ml/` 0 file.
- Perbedaan `docs/`: `main` punya `REPOSITORY_SIZE.md` dan perubahan `FINAL_SUBMISSION.md`; `development` belum.
  `dataset/README.md` dan `dataset/manifest.json` juga hanya ada di `main`.
- `development` melacak `backend/.DS_Store` (file sampah OS).
- Kesimpulan berbasis bukti: **`main` belum layak jadi production** untuk aplikasi yang sekarang dikerjakan, karena
  tidak memuat satu pun perubahan dashboard dan backend terbaru. Sebaliknya `main` berisi dokumen migrasi dan pembersihan
  yang `development` belum punya. Perlu satu PR `main` -> `development` (atau sebaliknya) sebelum `staging` dibuat.
  Apakah `main` stabil secara fungsional belum diuji di audit ini (hanya baseline dashboard di worktree dari `development`).

## 3. Verifikasi pemangkasan riwayat (pohon lama vs baru)

Dibandingkan: `development` lokal lama (c6bd8ef) vs `origin/development`; `main` lokal lama (4c58735) vs `origin/main`.

- **development**: tepat 10 file dihapus, 1.625.182 baris, seluruhnya data: `dataset/processed/{label_conflicts,test,train,val}.csv`,
  `dataset/raw/grambeddings/{train,test}.csv`, `dataset/raw/kaggle_malicious/malicious_phish.csv`,
  `dataset/raw/openphish/feed.txt`, `dataset/raw/tranco/tranco_Y8YYG.csv`, `dataset/raw/urlhaus/urlhaus_online.csv`.
  Tidak ada file diubah. Tidak ada file kode sumber (`.py .ts .tsx .js .css .html .sh .yml .md`) yang hilang.
- **main**: 10 file data yang sama dihapus; 5 file baru (`backend/test_clean_code.py`, `dataset/README.md`, `dataset/manifest.json`,
  `docs/REPOSITORY_SIZE.md`, `scripts/test_check_submission.cjs`); 8 file diubah (`.gitignore`, `README.md`, `README_SETUP.md`,
  `ai_anonymizer.py`, `ai_cache.py`, `behavior_service.py`, `FINAL_SUBMISSION.md`, `check_submission.cjs`). Itu cocok dengan 3 commit
  pemangkasan/refactor di atas. 1.625.279 baris dihapus total; 1.625.182 di antaranya dari 10 file data tadi, sisa 97 baris dari refactor.
- Data tetap ada di cadangan pribadi pemilik (`secrets/repo-optimization-20261011/` menurut dokumen migrasi). **Tanyakan ke Lovind lokasi
  persis penyimpanan dataset tersebut sekarang (belum ada LFS/Release).**
- Bobot model runtime `domain_v3` dan `char_bilstm.pt` masih ada di pohon baru.
- Tiga commit lokal lama (`6221f13`, `a1fc564`, `7e0c0a3`) punya padanan di remote dengan isi yang sudah dipangkas
  (`c03c939`, `27222a7`, `648d9de`). Kategori 3: menyentuh file yang dibuang saat slimming.
- Token bot Telegram: di ujung `main` dan `development` tidak ada pola token. Di **riwayat** `main`/`development`/`aria-dev` pola itu masih
  muncul di 12 commit (file: `Handoff.MD`, `n8n-workflows/flow-b*.json`, `start_webhook.py`, `sync_webhook.{py,ps1}`, `make_messaging_sequential.py`,
  `prepare_git_commit.py`), dan di ujung `ui/leaderboard-flat` (`Project Desc/Handoff.MD`). Pemangkasan tidak menghapusnya;
  dokumen migrasi sendiri menyebut kredensial harus dirotasi terpisah. **Pastikan token itu sudah dicabut/dirotasi.**

## 4. Branch yang diusulkan dihapus

Syarat: sudah ter-merge (dibuktikan `git branch -r --merged`) dan tidak punya commit unik (`git cherry` kosong).

| Branch | Alasan | Bukti |
| --- | --- | --- |
| `ui/leaderboard-flat` | Ter-merge ke `origin/development` dan `origin/main`, tidak ada commit unik | `git branch -r --merged origin/development` dan `origin/main` mencantumkannya; `git cherry` terhadap keduanya: 0 baris `+` |

Tidak diusulkan dihapus:

| Branch | Label | Alasan |
| --- | --- | --- |
| `feature/vps-deployment` | JANGAN DIHAPUS, perlu keputusan pemilik | 5 commit unik (`chore: streak maintenance 1-5`, hanya menambah baris di `streak_log.txt`), tidak ter-merge, 44 hari tanpa aktivitas. Tanyakan ke flyingsundaman. |
| `development`, `main` | Branch utama | - |
| `aria-dev`, `external` | Dikecualikan | Dipindahkan oleh pemiliknya sendiri |

## 5. Pertanyaan untuk pemilik

- flyingsundaman: apakah `feature/vps-deployment` (5 commit `streak maintenance`) boleh dibuang? Apakah ada pekerjaan deployment VPS lain yang hanya ada di lokal?
- Lovind: lokasi dataset hasil pemangkasan; apakah token Telegram lama sudah dirotasi; siapa admin repo dan paket GitHub apa yang dipakai.
- dapa: apakah `main` boleh digabung ke `development` (3 commit pemangkasan) sekarang.
- Pemilik `aria-dev` dan `external`: jadwal pemindahan (khusus `external`: bawa blob besar riwayat lama).

## 6. Langkah (BELUM dijalankan)

Sebelum menghapus branch apa pun, buat tag arsip di SHA terakhirnya:

```sh
git fetch origin
git tag archive/ui-leaderboard-flat 2951031     # SHA terakhir saat audit; cek ulang dengan git rev-parse origin/ui/leaderboard-flat
git push origin archive/ui-leaderboard-flat     # mengubah remote: perlu persetujuan
git push origin --delete ui/leaderboard-flat    # mengubah remote: perlu persetujuan
```

Selaraskan `development` dengan `main` tanpa merge riwayat lama (PR, bukan push langsung):

```sh
git switch -c chore/sync-main-into-development origin/development
git merge origin/main        # riwayat baru dengan riwayat baru; boleh. Jangan merge branch dari checkout lama
gh pr create --base development --head chore/sync-main-into-development --title "chore: sync main into development"
```

Buat `staging` dari `development` (setelah sinkron dan PR di atas ter-merge):

```sh
git fetch origin
git push origin origin/development:refs/heads/staging     # mengubah remote
```

Proteksi branch (keputusan 11 Oktober 2026: cukup `main`/production; `development` dan `staging` tidak diproteksi, tetapi tetap tanpa force-push sebagai kesepakatan):

| Branch | Wajib PR | Wajib CI lulus | Review | Force-push | Hapus branch |
| --- | --- | --- | --- | --- | --- |
| `main` | ya, hanya dari `staging`/`hotfix/*` | ya | 1 | dilarang | dilarang |

```sh
gh api -X PUT repositories/1280858980/branches/prod/protection --input protection.json   
```

Syarat: CI belum ada. Tambahkan workflow `.github/workflows/ci.yml` (tsc, eslint, `npm test`, build, `check_submission.cjs`)
sebelum mewajibkan status check.

**Catatan penting:** untuk repo private, proteksi branch bergantung pada paket GitHub (tersedia di Pro/Team/Enterprise,
tidak di akun Free). Panggilan `gh api .../branches/main/protection` dari akun ini mengembalikan 404 dan akun ini hanya punya izin WRITE,
jadi statusnya tidak bisa dipastikan. Admin repo (Lovind) perlu memeriksa Settings -> Branches dan paket yang dipakai.

Sampai CI dan proteksi aktif, disiplin PR berlaku sebagai kesepakatan tim.

## 7. Pemulihan

Cadangan ada di `~/Documents/Afferent-backup-worktrees-20261011/`: `internal-all-branches.bundle`, `origin-mirror-20261011.git`,
`snapshot-before/`, `patches-category2/`. Tag lokal `backup/*-20261011` melindungi SHA lama dari garbage collection.
Pulihkan satu branch: `git fetch ~/Documents/Afferent-backup-worktrees-20261011/internal-all-branches.bundle <branch>:restored/<branch>`.
Pulihkan satu file dari mirror: `git --git-dir=~/Documents/Afferent-backup-worktrees-20261011/origin-mirror-20261011.git show <ref>:<path> > <path>`.
