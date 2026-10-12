# Kontribusi

Repo ini belum punya CI, template PR/issue, atau CODEOWNERS (`.github/` tidak ada). Aturan di bawah mengikuti
[BRANCHING.md](BRANCHING.md); jika ada beda, BRANCHING.md yang berlaku.

## Alur singkat

1. Ambil checkout baru dari GitHub (jangan memakai checkout lama sebelum pemangkasan riwayat 11 Oktober 2026;
   lihat [README_SETUP.md](../README_SETUP.md)).
2. Buat branch dari `development`: `git fetch && git switch -c <jenis>/<topik> origin/development`.
   Jenis: `feat/`, `fix/`, `ui/`, `docs/`, `chore/`, `hotfix/` (hotfix dari `prod`).
3. Commit kecil dengan pesan `jenis(lingkup): ringkasan` (contoh: `fix(bff): expose second-opinion through the proxy allowlist`).
4. Jalankan pemeriksaan di bawah, lalu buka PR ke `development`.
5. `development` -> `staging` -> `prod` hanya lewat PR. Jangan push langsung ke ketiganya dan jangan force-push.

Beberapa orang memakai satu folder yang sama di komputer ini; gunakan `git worktree add` supaya tidak saling
mengganti branch.

## Pemeriksaan sebelum PR

Dashboard (`dashboard/`):

```sh
npx tsc --noEmit
npm run lint
npm test
USE_MOCKS=true APP_ENV=local npm run build
```

Backend dan repo:

```sh
python -m unittest discover -s backend -p "test_*.py"
node scripts/check_submission.cjs --staged
```

Semua tes di atas sudah ada di `development`. Teks UI lewat `dashboard/src/i18n/messages.ts` (ID/EN).

## Yang tidak di-commit

Screenshot, PDF hasil render, dataset besar, bobot/checkpoint model, `.env`, kunci, database. Lihat bagian
file besar di [BRANCHING.md](BRANCHING.md) dan `.gitignore`. Jangan menaruh rahasia di commit; riwayat lama
masih memuat pola token lama (lihat [REPO_CLEANUP_PLAN.md](REPO_CLEANUP_PLAN.md)).
