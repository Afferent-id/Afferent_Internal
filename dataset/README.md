# Training data (optional)

The application does not read the bulk CSVs in this directory at runtime.
The deployed domain model and compatibility artifacts remain in `backend/models/`.
Only dataset documentation, statistics, a small case study and
[`manifest.json`](manifest.json) are versioned here. Training code/notebooks remain
in the repository; large corpora are kept outside normal Git history.

## Restore the frozen data for retraining

Request `training-data-local.zip` from the repository owner. The owner keeps a
private recovery copy in `secrets/repo-optimization-20261011/`. Extract the archive
into the repository root; its entries start with `dataset/`. Check the SHA-256
values in `manifest.json` before using the data. These hashes describe the owner's
byte-exact snapshot, including its original line endings; do not normalize the CSVs.
Do not overwrite existing datasets without first preserving your current copy.

The archive is not yet published as a GitHub Release. Do not assume that a download
URL exists. Publish/share only the dataset archive after reviewing its source
licenses; never distribute `history-before.bundle`, ENV files, secrets or CA keys.

`training-data-before.zip` is a separate Git-committed snapshot for recovery, not
the byte-identical training archive; older checkouts may have different line endings.

## Sources and reproducibility

See [`processed/dataset_card.md`](processed/dataset_card.md) for the original
source references, licensing notes, split statistics and frozen experiment hashes.
`dataset_builder.py` can rebuild a corpus from independently acquired source data,
but current threat feeds are mutable and are not an exact replacement for the
frozen archive. Supplied labels and old dataset claims are not newly revalidated
by this repository-size cleanup.

Raw/processed corpora, caches, LLM weights and checkpoints are ignored locally.
Do not force-add them to Git. Use an approved release asset or separate research
storage for future large artifacts, with checksums and provenance.
