# Repository size and team migration

## Scope

Keep application code, runtime models, dataset provenance and evaluation reports
in Git. Keep bulk training corpora, downloaded LLM weights and checkpoint/optimizer
outputs outside ordinary Git history. This cleanup does not change proxy policy,
authentication, SOC decisions or the advisory-only local LLM feature.

On 11 October 2026, local Git packs occupied 288.28 MiB. Current tracked datasets
occupied about 113.27 MiB before compression. Old MiniLM weights and LLM training
checkpoints remained reachable from older commits. These measurements are local
storage sizes, not an exact GitHub network-transfer measurement.

## Completed local preparation

- Preserve bulk data locally while removing it from the Git index.
- Preserve runtime model files byte-for-byte, including `domain_v3` and Char-BiLSTM.
- Retain source documentation, dataset statistics, case study and SHA-256 manifest.
- Ignore corpora, generated exports and offline weights/checkpoints.
- Extend the existing submission guard: 10 MiB per file, 25 MiB in total.
- Keep a private recovery ZIP for the working-copy datasets, a ZIP of committed
  datasets and a verified Git bundle at `secrets/repo-optimization-20261011/`.

The Git bundle contains historical material, potentially including old exposed
credentials. It is private recovery data, not a release asset. It does not revoke
any credential; rotate exposed keys independently.

## Remaining shared-history step

A normal commit deleting a large file does **not** remove its earlier Git objects.
Local preparation alone therefore does not fix the size of an ordinary fresh clone
from the existing GitHub history. Do not describe it as completed remote optimization.

History replacement/force-push requires the repository owner's explicit approval
and coordination with teammates. The remote currently has five branches and the
`pre-ui-merge` tag. Both `main` and `aria-dev` point to the old `4c58735` history;
rewriting `main` alone would leave the same large objects reachable through
`aria-dev`. An ordinary clone fetches other branches too. Approve the exact refs
to rewrite after checking each branch/tag; do not delete teammates' branches.
Before publication:

1. Stop team pushes and preserve uncommitted work outside the repository.
   Anyone with tracked training CSVs should archive them before pulling the cleanup
   commit: Git removes those tracked copies during an update. Only the owner's
   current `git rm --cached` operation preserves its existing local copies in place.
2. Verify backups and remote branch/tag heads; do not discard teammate changes.
3. Rewrite only approved refs in an isolated copy. Preserve runtime files and keep
   provenance/commit mapping. Audit any other branches/tags retaining large objects.
4. Run the submission guard and model-checksum checks. Test an ordinary fresh clone
   of the candidate and measure its pack size before touching GitHub.
5. Publish approved refs with explicit expected old hashes (`--force-with-lease`),
   never blind `--force` or `--mirror`. Do not delete unrelated branches/tags.
6. Verify an ordinary GitHub clone. Have teammates make a fresh checkout and copy
   only their own changes; do not merge/push the old history back into cleaned refs.

No remote history replacement or branch/tag deletion has been performed by the
local preparation. See [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Temporary lightweight clone

Until shared history has been cleaned, this uses only the latest application files.
Run in a parent directory; choose a new destination name if it already exists.

```sh
git -c http.version=HTTP/1.1 clone --depth 1 --single-branch --branch main --no-tags --filter=blob:none --sparse https://github.com/Llovind/Human_Firewall.git Human_Firewall-demo
cd Human_Firewall-demo
git -c http.version=HTTP/1.1 sparse-checkout set backend dashboard gophish proxy ml scripts docs
```

This procedure was tested against commit `4c58735`; local resulting Git packs were
7.32 MiB. It is a measured workaround, not a guarantee for another network. A new
checkout still needs private ENV/PKI initialization; never overwrite the existing
installation or delete Docker volumes just to test a clone.

## Prevent recurrence

Before committing/publishing:

```sh
node scripts/check_submission.cjs
node scripts/test_check_submission.cjs
node scripts/check_submission.cjs --staged
```

Restore corpora only for research tasks following [dataset instructions](../dataset/README.md).
Upload approved, non-secret large artifacts separately with source/license notes
and checksums. A new release or LFS migration has not yet been published.
