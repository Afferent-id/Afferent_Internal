# Alur branch

Status: **usulan**, belum disetujui tim (Lovind dan Farrel). Alur `staging` baru berlaku setelah
branch itu dibuat (lihat [REPO_CLEANUP_PLAN.md](REPO_CLEANUP_PLAN.md)). Sampai saat itu, `development`
adalah branch integrasi dan `main` tetap dipakai apa adanya.

## Alur

```
feat/* fix/* ui/* docs/* chore/*  ->  development  ->  staging  ->  main (production)
                                                                      ^
                                              hotfix/* ---------------+  (lalu back-merge ke development)
```

| Branch | Fungsi | Siapa yang boleh mengubah |
| --- | --- | --- |
| `development` | Integrasi pekerjaan harian. Harus selalu lulus lint, test, build. | Hanya lewat PR dari feature branch |
| `staging` | Kandidat rilis, dicoba di lingkungan uji (demo VM/lab). | Hanya lewat PR dari `development` |
| `main` | Production. Yang ada di sini adalah yang dipakai/dirilis. | Hanya lewat PR dari `staging` (atau `hotfix/*`, lihat bawah) |

Branch `aria-dev` dan `external` berada di luar alur ini. Keduanya akan dipindahkan oleh pemiliknya
dan tidak diatur dokumen ini.

## Penamaan branch

`<jenis>/<topik-singkat-huruf-kecil-dengan-tanda-hubung>`

| Awalan | Untuk | Contoh |
| --- | --- | --- |
| `feat/` | Fitur baru | `feat/access-request-expiry` |
| `fix/` | Perbaikan bug | `fix/bff-second-opinion-allowlist` |
| `ui/` | Perubahan tampilan tanpa logika baru | `ui/polish-v2` |
| `docs/` | Dokumentasi saja | `docs/prd-srs-internal` |
| `chore/` | Perawatan, dependensi, konfigurasi, CI | `chore/gitignore-os-files` |
| `hotfix/` | Perbaikan mendesak untuk production | `hotfix/session-expiry` |

Repo saat ini juga punya `feature/vps-deployment`; untuk branch baru pakai `feat/`, bukan `feature/`.

## Aturan PR

- Target default: `development`. Target `staging` hanya dari `development`; target `main` hanya dari `staging` atau `hotfix/*`.
- Merge `staging` -> `main` hanya lewat PR, tidak pernah push langsung.
- Minimal 1 reviewer yang bukan pembuat PR. Perubahan di `backend/` (auth, proxy, database) sebaiknya direview
  oleh orang yang memegang bagian itu. `TODO: konfirmasi siapa reviewer default untuk tiap folder`.
- Sebelum membuka PR jalankan pemeriksaan yang sama dengan CI (lihat [CONTRIBUTING.md](CONTRIBUTING.md)).
- PR kecil dan fokus satu topik. Jangan menyertakan screenshot, PDF, atau model baru di PR.
- Jangan force-push ke `main`, `staging`, atau `development`. Pada feature branch sendiri boleh, selama
  belum ada orang lain yang memakainya.
- Strategi merge: `TODO: pilih squash atau merge commit`. Riwayat saat ini memakai merge commit.

## Hotfix

Hotfix boleh langsung masuk `main` hanya jika production rusak atau ada celah keamanan yang tidak bisa menunggu
siklus staging:

1. Cabang dari `main`: `hotfix/<topik>`.
2. PR ke `main` dengan 1 reviewer dan CI lulus.
3. Segera setelah merge, back-merge `main` ke `development` (dan `staging` bila ada) lewat PR, supaya
   perbaikan tidak hilang pada rilis berikutnya.

## Konvensi commit

Yang sudah dipakai repo: Conventional Commits huruf kecil `jenis(lingkup opsional): ringkasan`.
Jenis yang ada di riwayat: `fix`, `feat`, `style`, `docs`, `chore`, `security`, `refactor`, `test`, `ux`.
Contoh nyata: `fix(bff): expose second-opinion through the proxy allowlist`,
`feat(theme): follow prefers-color-scheme when no theme is saved`.
Hindari commit tanpa jenis dan `wip`.

## File besar dan file yang tidak di-commit

- Tidak di-commit: dataset mentah/besar, bobot model hasil unduhan, checkpoint training, screenshot, PDF hasil
  render, `.env`, kunci/sertifikat, database SQLite, `.DS_Store`.
- Simpan di luar repo (mis. folder `_non-code/` lokal atau storage tim) dan catat lokasinya di dokumen terkait.
- Model yang dibutuhkan aplikasi saat runtime (`backend/models/domain_v3`, Char-BiLSTM) tetap di Git selama
  kecil. Batas yang diperiksa `node scripts/check_submission.cjs`: 10 MiB per file, 25 MiB total.
- Jika ada artefak besar yang harus dibagikan, pakai GitHub Release atau Git LFS. Keduanya **belum disiapkan**
  (lihat `docs/REPOSITORY_SIZE.md` di `main`). Putuskan dulu sebelum mulai.
- Riwayat repo dipangkas pada 11 Oktober 2026. Jangan merge atau push riwayat checkout lama; ambil perubahan
  dengan `git cherry-pick` atau patch ke branch baru dari `origin/development`.
