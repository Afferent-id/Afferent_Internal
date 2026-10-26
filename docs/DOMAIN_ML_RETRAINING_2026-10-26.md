# Domain ML retraining: release decision

Date: 26 October 2026. Product: Afferent Reflex. **No new candidate promoted.**
Live traffic continues to use `domain_v3`, with SOC Block/Allow authoritative.
VirusTotal, urlscan and local LLMs are absent from live classification, including
background jobs. Explicit employee URL/file scanning retains its providers.

## What was actually tested

Prepared local Grambeddings/Kaggle snapshots plus the existing training split:
457,439 unique pure-label training hosts, 125,030 validation rows and 54,502
newly reserved test observations (54,222 unique hosts). Registered-domain overlap
between splits is zero. Frozen legacy validation/test groups are excluded from
new training. Mixed-label hosts are excluded from training but both labels are
retained in evaluation. Neither URLs nor page contents were fetched.

The core class labels originally describe URLs, including compromised sites.
A hostname cannot distinguish two differently labelled paths on the same site.
The category CSV was audited separately: 8,778 general, 4,184 gambling, 2,160
adult and 1,100 streaming hosts. These were not relabelled as phishing/malware
or used in this binary experiment. The unverified LLM/SFT labels were not used.

Algorithms/configurations actually fitted:

- Character TF-IDF + Logistic Regression, C=1 and 4.
- The same plus 13 structural features: length, label count, character ratios,
  entropy and IDNA structure, C=1 and 4.
- Character features plus the frozen previous model margin, C=1 and 4.
- Histogram Gradient Boosting, 15/31 leaves, 180 iterations, structural features
  plus frozen character-model margin. Excluded 83,353 hosts in prior fitting
  groups; this booster fitted 374,086 hosts.
- Character TF-IDF + LinearSVC, C=0.25, 1 and 4, with separate Platt calibration.
- A fixed conservative maximum-risk ensemble of the previous model and the
  booster. It keeps the highest member threshold, without another threshold
  search. Its output is a risk score, **not a joint calibrated probability**.

Classifier parameters are selected on policy-validation groups; calibration
groups are separate. The first LR experiment used a 0.30% validation FPR upper
budget; subsequent challengers used a stricter 0.15% validation margin against
the unchanged 0.30% release limit. Later choices followed earlier development
results, so these tests are **reused development evidence**, not untouched tests.

## Results at each model's proposed blocking threshold

All numbers below include the generated-host abstention rule. Recall means the
fraction of labelled malicious observations blocked, not overall accuracy.
FPR is false positives divided by benign observations.

| Candidate | New-group recall | New-group FPR | Legacy recall | Legacy FPR | Warm CPU p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing v3 LR | 5.90% | 0.052% | 21.18% | 0.098% | ~1.2 ms |
| Expanded LR | 23.10% | 0.280% | 15.79% | 0.425% | 1.07 ms |
| LR + structure | 17.98% | 0.124% | 11.71% | 0.196% | 2.66 ms |
| LR + frozen prior | 17.09% | 0.109% | 11.31% | 0.196% | 3.01 ms |
| Histogram boosting + prior | 14.66% | 0.168% | 11.26% | 0.098% | 5.46 ms |
| Calibrated LinearSVC | 15.06% | 0.104% | 8.96% | 0.196% | 0.91 ms |
| Conservative LR/boosting ensemble | 12.25% | 0.114% | 26.35% | 0.163% | 8.32 ms |

No candidate passed **all** release checks: FPR Wilson 95% upper bound <=0.30%
on both cohorts, improved new-group recall, no legacy-recall regression, no
blocked benign sentinel, warm p95 <10 ms and artifact <10 MiB. The ensemble
raised legacy true positives from 893 to 1,111 but false positives from 3 to 5;
its FPR upper bound was **0.382%**, so it was rejected. We did not relax the gate
or whitelist those errors. The existing v3 upper bound is 0.288% on that cohort.

Unknown remains substantial: v3 97.01% on new groups / 86.73% on legacy;
the rejected ensemble 95.14% / 83.72%. These experiments do not establish broad
phishing coverage, adult/gambling detection or readiness for unattended rollout.

Machine-readable counts, metrics, artifact IDs, hashes and gate failures:
[evaluation JSON](evaluations/domain_ml_2026-10-26.json).
Paper/algorithm analysis: [research review](DOMAIN_ML_ALGORITHM_REVIEW.md).

## Reproduce offline

Use the pinned backend ML dependencies and `requirements-training.txt` for
preparation (`tldextract==5.3.0`, bundled PSL, no live suffix download). Restore
the raw snapshots using [dataset instructions](../dataset/README.md). Do not
overwrite an existing output directory or an evaluated runtime artifact.

```bash
cd backend
python prepare_domain_corpus.py --dataset ../dataset --category-csv /path/to/labeled_data_final.csv --output ../ml/artifacts/new_data
python train_domain_model.py --dataset ../ml/artifacts/new_data --output ../ml/artifacts/new_lr --fpr-budget 0.003 --c-values 1 4
python train_domain_model.py --dataset ../ml/artifacts/new_data --output ../ml/artifacts/new_hgb --algorithm hgb --structural-features --baseline-features models/domain_v3 --exclude-training-groups ../dataset/processed/train.csv --fpr-budget 0.003 --policy-fpr-budget 0.0015 --max-leaves 15 31
python compare_domain_models.py --baseline models/domain_v3 --candidate ../ml/artifacts/new_hgb --fresh ../ml/artifacts/new_data --legacy ../dataset/processed --output ../ml/artifacts/new_hgb_comparison.json
```

Runs used isolated containers, no inference network, 4 CPUs and <=4 GiB memory.
Timing is warm model inference only, excluding application/proxy/database/network;
resource contention differs across runs, so small timing differences are not
proof of a faster algorithm. Training corpora/candidates remain ignored under
`ml/artifacts`, outside normal Git downloads. The active artifact is unchanged.
Wilson bounds here treat host-label observations as independent; correlated
subdomains within a registered-domain group are not cluster-adjusted. These
are conservative engineering gates on this corpus, not population guarantees.
Per-training `enforcement_eligible` only described its own holdout gate in these
experiments; the full release comparison is authoritative. Do not point runtime
ENV at a candidate whose comparison says `promotable: false`.

## Next evidence needed

Freeze new, time-separated and independently checked **hostname** labels before
further model selection, including current benign cloud/CDN/service traffic and
current phishing/malware hosts. Keep mixed/shared hosts explicitly ambiguous.
Evaluate category policy separately with the confirmed CSV label mapping and
manual verification. LightGBM/XGBoost and a small character CNN remain untested
challengers; no claim that either is best follows from these results.
