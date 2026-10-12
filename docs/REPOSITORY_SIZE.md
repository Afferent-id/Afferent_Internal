# Repository size and team migration

## Scope

Keep application code, runtime models, dataset provenance and evaluation reports
in Git. Keep bulk training corpora, downloaded LLM weights and checkpoint/optimizer
outputs outside ordinary Git history. This cleanup does not change proxy policy,
authentication, SOC decisions or the advisory-only local LLM feature.

On 11 October 2026, repository history was slimmed and published with the owner's
approval. Full-history GitHub clone verification passed without shallow, sparse
or blob-filter options.

| Measurement | Before | After |
| --- | ---: | ---: |
| Git pack storage in a full GitHub clone/mirror | 287.89 MiB | 10.80 MiB |
| Current publishable indexed content | about 124 MiB | 10.98 MiB |

Pack storage decreased by approximately 96.2%. These are measured local storage
sizes, not a network-bandwidth guarantee. Slow or unstable connections can still
cause Git transport errors.

## Completed optimization

- Preserve bulk data locally while removing it from the Git index.
- Preserve runtime model files byte-for-byte, including `domain_v3` and Char-BiLSTM.
- Retain source documentation, dataset statistics, case study and SHA-256 manifest.
- Ignore corpora, generated exports and offline weights/checkpoints.
- Extend the existing submission guard: 10 MiB per file, 25 MiB in total.
- Keep a private recovery ZIP for the working-copy datasets, a ZIP of committed
  datasets and a verified Git bundle at `secrets/repo-optimization-20261011/`.
- Remove 19 exact bulk-corpus, offline-weight, tokenizer and checkpoint paths
  across the shared history, not just from the current working tree.
- Preserve all 124 pre-migration and cleanup commits, their author/committer
  metadata and messages. Verify every commit tree changes only at those paths.
- Preserve all five branch names and the `pre-ui-merge` tag. The unaffected
  `feature/vps-deployment` head remains unchanged; no branch/tag was deleted.
- Publish the checked refs atomically using explicit old-hash leases. Check the
  resulting GitHub refs and an ordinary fresh clone with `git fsck` and the guard.

The Git bundle contains historical material, potentially including old exposed
credentials. It is private recovery data, not a release asset. It does not revoke
any credential; rotate exposed keys independently.

## Normal clone and team migration

Run in a parent directory and choose a new destination name if it already exists:

```sh
git clone https://github.com/Afferent-id/Afferent_Internal.git Afferent_Internal-clean
cd Afferent_Internal-clean
```

Do not merge or push an old checkout's history back into the cleaned repository;
doing so makes removed objects reachable again. Before moving to a new checkout:

1. Preserve uncommitted work and any local-only commits. Keep the old folder as a
   recovery copy rather than deleting it.
2. Archive training CSVs, private ENV/PKI and data separately. Do not distribute
   secrets or copy generated directories into the new Git index.
3. Clone into a new folder and reapply only necessary source changes. Review each
   patch/cherry-pick and the guard before pushing; avoid merging old branches.
4. Restore private configuration following [lab setup](../README_SETUP.md), using
   existing server data/CA material where appropriate. Never delete Docker
   volumes or reinitialize an existing installation just to test a clone.

The owner's existing checkout was aligned only after proving its file tree was
identical to the published code. It still holds old objects and private backups
for recovery, so its `.git` size is not the fresh-clone measurement above. Do not
upload that folder as a release ZIP.

Private rollback evidence includes `history-before.bundle`, a fresh original
remote mirror, dataset archives, incremental cleanup bundles and the verified
original-to-clean commit map. Restoring shared history requires explicit team
coordination and new leases; rollback is not an automatic destructive command.
The source commit IDs in old dataset records refer to the original history.

See [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

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

## Behavior-preserving code cleanup

The cleanup also removes concrete duplication without changing security policy:

- `backend/ai_cache.py` uses standard-library `contextlib.closing` instead of
  seven repeated `try/finally` blocks. SQLite transaction commit/rollback and
  connection closure remain separate and explicit; TTL and error behavior stay unchanged.
- `backend/ai_anonymizer.py` reuses the same per-user and batch pseudonymization
  functions for compatibility callers. Restoration iterates only the two
  supported response fields, retaining its existing in-place semantics.
- `backend/services/behavior_service.py` separates baseline risk rules,
  per-employee classification and organization aggregation. Thresholds, output
  fields, text and division tie-breaking are unchanged.
- `backend/test_clean_code.py` adds 24 offline characterization checks, first
  passed against the original code, then against each refactor. They use a new
  temporary SQLite database, not the owner's application database.

Run the focused checks without a Docker daemon or external API credentials:

```sh
python -m unittest discover -s backend -p test_clean_code.py
```

Verification on 11 October 2026:

- All 55 existing backend regressions and the 24 new checks passed inside the
  existing Python 3.10 application image with the current source mounted read-only,
  networking disabled and disposable temporary databases.
- The existing three dashboard regression scripts, eight repository-guard checks,
  two lab-setup checks, Compose configuration and Python syntax compilation passed.
- The offline denial-page renderer passed inside the existing proxy image.
- All six runtime artifacts retained their checksums. Ten local datasets and their
  private ZIP entries matched the recovery manifest.
- The candidate and the real full GitHub clone passed integrity/size guards.
  No reachable blob in the cleaned shared history exceeded the 10 MiB budget.

This pass did not redeploy running services, rebuild application images, or repeat
the two-device live-network demo. The existing report suite emitted a resource
warning but passed; it is not represented as a warning-free integration run.

This is targeted refactoring, not a wholesale rewrite. The large legacy SQLite
module and its timestamp compatibility semantics remain deferred; converting
naive timestamps or restructuring authentication/proxy code requires its own
migration and integration tests. No dependencies were added to the application.
