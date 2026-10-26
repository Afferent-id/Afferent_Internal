# Domain ML algorithm review

Research date: 26 October 2026. Scope: Afferent Reflex live proxy traffic.

Local benchmark completed: LR variants, calibrated LinearSVC, histogram
boosting and a conservative ensemble were tested. No challenger passed every
release check, so the existing v3 LR remains active. See the
[measured retraining results](DOMAIN_ML_RETRAINING_2026-10-26.md).

## Recommendation

**Benchmark calibrated histogram gradient boosting against the existing character
n-gram linear model first. There is no evidence yet that one algorithm is the
best for Afferent.** Start with scikit-learn's `HistGradientBoostingClassifier`,
which is already available in the pinned ML environment. Compare LightGBM or
XGBoost only if a measured benefit justifies another runtime dependency.

This is an engineering recommendation, not a claim that boosting has won the
local evaluation. Histogram boosting can learn nonlinear interactions in compact
numeric features; scikit-learn documents its suitability for large tabular
datasets and its relationship to LightGBM. It does not accept the sparse TF-IDF
matrix as a drop-in replacement. Use hostname structure and, if useful, a
properly evaluated character-model score as compact inputs.
[scikit-learn 1.6 ensemble guide](https://scikit-learn.org/1.6/modules/ensemble.html#histogram-based-gradient-boosting).

The deployment contract remains: SOC Block/Allow first, cached policies next,
local ML for uncached hostnames. No VirusTotal, urlscan, LLM, DNS/WHOIS lookup,
page fetch, or TLS payload inspection is part of this live classification path.

## Candidate shortlist

| Candidate | Appropriate experiment | Limitation and decision |
| --- | --- | --- |
| TF-IDF character n-grams + Logistic Regression | Retain the measured baseline and test improved training/calibration. Sparse text classification is a supported use of linear models. | Fast baseline; cannot express every interaction. Keep it unless another candidate wins the release checks. [Official comparison](https://scikit-learn.org/1.6/auto_examples/text/plot_document_classification_20newsgroups.html). |
| TF-IDF + LinearSVC + calibration | A low-complexity challenger using the same sparse features. | Its decision margin is not a probability; calibrate on separate domain groups. [LinearSVC](https://scikit-learn.org/1.6/modules/generated/sklearn.svm.LinearSVC.html), [calibration](https://scikit-learn.org/stable/modules/calibration.html). |
| Histogram gradient boosting | First nonlinear challenger on length, label counts, entropy, character ratios and a frozen character-model margin. | Evaluate standalone and combined features; do not fit an upstream model on held-out labels. Already available in scikit-learn. [Official guide](https://scikit-learn.org/1.6/modules/ensemble.html#histogram-based-gradient-boosting). |
| LightGBM / XGBoost | Further CPU boosting comparisons if needed. | LightGBM uses histogram binning and leaf-wise growth; control complexity. XGBoost offers a histogram tree method. Neither documentation proves lower FPR on this corpus. [LightGBM](https://lightgbm.readthedocs.io/en/stable/Features.html), [XGBoost](https://xgboost.readthedocs.io/en/stable/treemethod.html). |
| CatBoost | Consider when meaningful categorical features are available, such as well-supported suffix categories. | Its categorical/text processing is useful functionality, not evidence of superiority for hostname-only detection. Avoid treating a complete unique hostname as a reusable category. [Official feature handling](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic). |
| Small character CNN | A later hostname-trained challenger if lexical models plateau. | URLNet learns from characters and words in complete URL strings; its published result cannot validate a hostname-only replacement. A new hostname experiment and CPU timing are required. [URLNet authors' paper](https://arxiv.org/abs/1802.03162). |

## What the papers actually support

The 2022 Alhogail/Al-Turaiki study supports testing gradient boosting, but its
headline result uses **both host-based and lexical features**. Table 3 reports
lexical-only GBM accuracy of 95.60% with FPR **5.79%**. Table 4 reports combined
features GBM accuracy of 98.98% with FPR **0.30%**; that feature set includes
DNS/WHOIS/HTTP information absent from this proxy model. Those are results at
the paper's operating points and evaluation protocol, not Afferent guarantees.
The difference also illustrates why headline accuracy is an unsuitable release
criterion. [Publisher's full paper, Tables 1, 3 and 4](https://itc.ktu.lt/index.php/ITC/article/view/30380/15385).

The NIST-authored 2022 study investigates **algorithmically generated domains**,
using lexical-distance features and multiple learning methods. Its results
support feature engineering, but DGA detection is a narrower task than phishing,
compromised legitimate sites, gambling, or adult-content classification.
[NIST publication](https://www.nist.gov/publications/machine-learning-based-algorithmically-generated-domain-detection).

## Benchmark and promotion rules

1. Freeze the candidate list and split by registered domain. A domain group must
   never occur in both fitting and held-out evaluation; grouped validation is
   designed to detect this form of leakage.
   [Group validation documentation](https://scikit-learn.org/1.6/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
2. Fit vocabulary/features/classifier on training only. Fit calibration and
   select the blocking threshold on separate validation groups. Calibration data
   must be disjoint from classifier fitting data.
   [Official calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).
3. Select by recall under the declared low-FPR constraint, then measure precision,
   Unknown coverage, warm single-host CPU p50/p95, artifact size and memory.
   Afferent's proposed release criterion is a 95% Wilson FPR upper bound at most
   0.30%, not merely an observed FPR below that value.
4. Preserve mixed-label hosts in evaluation: different paths on the same host
   can have different labels. Report a reused legacy test as a regression set;
   newly reserved groups from the same historical sources are not a temporal or
   independent-source validation set. Repeated experiments also weaken the
   interpretation of an untouched holdout.
5. Test legitimate cloud/CDN/service hostnames and retain conservative abstention
   outside supported input patterns. Report these regression checks separately
   from statistical performance. Never manufacture a safe verdict to reduce
   the Unknown count.

## Input and dataset limits

A hostname-only classifier receives the same input for a benign page and a
phishing page on the same host. Changing the algorithm cannot recover the hidden
path or page content. Likewise, a gambling/adult category is not a phishing label;
evaluate those policies with suitable category labels, and keep streaming label
3 separate as agreed. No blanket `.com` whitelist is justified.

The current baseline, its conservative threshold, and historical limitations
are recorded in [DOMAIN_ML_EVALUATION.md](DOMAIN_ML_EVALUATION.md) and the
[domain_v3 manifest](../backend/models/domain_v3/manifest.json). This research note
does not declare any pending retraining candidate promoted.
