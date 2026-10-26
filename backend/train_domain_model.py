"""Train/evaluate a domain-only candidate offline; never fetch dataset URLs.

Training uses train.csv only. val.csv is split by registered domain into
calibration and threshold-policy subsets. Frozen test.csv is evaluated once;
it never fits vocabulary, coefficients, calibration, or thresholds.
"""
import argparse
import csv
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from services.proxy_service import normalize_domain, ProxyError


def load(path):
    rows = []
    rejected = 0
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                host = normalize_domain(row["url"])
            except (ProxyError, ValueError):
                rejected += 1
                continue  # counted, not silently repaired or fetched
            label = int(row["is_malicious"])
            if label not in (0, 1):
                raise ValueError("Non-binary dataset label")
            rows.append((host, label, row["registered_domain"].lower().rstrip(".") or host))
    return rows, rejected


def upper_error(count, total):
    """95% Wilson upper bound: zero observed errors does not mean zero risk."""
    if total == 0:
        return 1.0
    z, p = 1.96, count / total
    return (p + z*z/(2*total) + z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))) / (1 + z*z/total)


def select_threshold(y, probabilities, budget):
    # Select highest recall under the policy-validation FPR upper-bound budget.
    # >= comparison accounts for tied calibrated scores (no optimistic slicing).
    negatives = int((y == 0).sum())
    best = None
    order = np.argsort(-probabilities, kind='stable')
    scores, labels = probabilities[order], y[order]
    cumulative_fp = np.cumsum(labels == 0)
    cumulative_tp = np.cumsum(labels == 1)
    # Inspect only the END of each score tie: all equal scores are blocked.
    ends = np.flatnonzero(np.r_[scores[:-1] != scores[1:], True]) if len(scores) else []
    for index in ends:
        threshold = scores[index]
        fp, tp = int(cumulative_fp[index]), int(cumulative_tp[index])
        if tp and upper_error(fp, negatives) <= budget:
            candidate = (tp, -fp, float(threshold))
            if best is None or candidate > best:
                best = candidate
    return best[2] if best else None


def metrics(rows, probabilities, threshold):
    y = np.array([r[1] for r in rows])
    blocked = probabilities >= threshold if threshold is not None else np.zeros(len(y), dtype=bool)
    fp, tp = int(((y == 0) & blocked).sum()), int(((y == 1) & blocked).sum())
    negatives, positives = int((y == 0).sum()), int((y == 1).sum())
    return {"rows": len(rows), "unique_domains": len({r[0] for r in rows}),
        "benign": negatives, "malicious": positives,
        "binary_accuracy_at_0_5": float(accuracy_score(y, probabilities >= 0.5)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "block_false_positives": fp, "block_true_positives": tp,
        "block_fpr": fp / negatives if negatives else None,
        "block_fpr_95pct_upper": upper_error(fp, negatives),
        "block_precision": tp / (tp + fp) if tp + fp else None,
        "block_recall": tp / positives if positives else None,
        "unknown_fraction": float((~blocked & (probabilities > 0.1)).mean())}


def distinct_domain_labels(rows, probabilities):
    # Repeated URL paths on one host are not independent domain decisions.
    # Retain both labels for mixed hosts: one benign path is enough to count
    # a whole-domain block as a false positive for that host.
    unique = {(r[0], r[1]): (r, float(p)) for r, p in zip(rows, probabilities)}
    return [v[0] for v in unique.values()], np.array([v[1] for v in unique.values()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parent.parent / "dataset/processed")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "models/domain_v1")
    parser.add_argument("--fpr-budget", type=float, default=0.01)
    parser.add_argument("--c-values", type=float, nargs='+', default=[4.0], help='Choose on policy validation only, never test scores')
    parser.add_argument('--structural-features', action='store_true')
    parser.add_argument('--baseline-features', type=Path, help='Trusted frozen prior domain model, as a feature; not refitted')
    parser.add_argument('--algorithm', choices=('lr', 'svm', 'hgb'), default='lr')
    parser.add_argument('--max-leaves', type=int, nargs='+', default=[15, 31])
    parser.add_argument('--exclude-training-groups', type=Path, help='Prior fitting groups to exclude when using a frozen model as a feature')
    parser.add_argument('--policy-fpr-budget', type=float, help='Optional stricter validation budget, providing release margin')
    args = parser.parse_args()
    if not 0 < args.fpr_budget < 0.1:
        raise ValueError("Use a realistic low FPR budget in (0, 0.1)")
    if any(not math.isfinite(value) or value <= 0 for value in args.c_values):
        raise ValueError('C values must be finite and positive')
    policy_budget = args.policy_fpr_budget if args.policy_fpr_budget is not None else args.fpr_budget
    if not 0 < policy_budget <= args.fpr_budget:
        raise ValueError('Policy budget must be positive and no greater than the release budget')
    if args.output.exists():
        raise ValueError("Candidate output already exists; do not overwrite evaluated artifacts")
    loaded = {name: load(args.dataset / f"{name}.csv") for name in ("train", "val", "test")}
    splits = {name: value[0] for name, value in loaded.items()}
    groups = {name: {r[2] for r in rows} for name, rows in splits.items()}
    overlaps = {f"{a}/{b}": len(groups[a] & groups[b]) for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
    if any(overlaps.values()):
        raise ValueError(f"Registered-domain leakage across supplied splits: {overlaps}")
    labels = defaultdict(set)
    for host, label, _ in splits["train"]:
        labels[host].add(label)
    training = [(host, next(iter(values))) for host, values in sorted(labels.items()) if len(values) == 1]
    excluded_prior_groups = 0
    if args.exclude_training_groups:
        previous_groups = {row[2] for row in load(args.exclude_training_groups)[0]}
        allowed_hosts = {row[0] for row in splits['train'] if row[2] not in previous_groups}
        before = len(training)
        training = [row for row in training if row[0] in allowed_hosts]
        excluded_prior_groups = before - len(training)
    calibration, policy = [], []
    for row in splits["val"]:
        bucket = int(hashlib.sha256(row[2].encode()).hexdigest()[:8], 16) % 2
        (calibration if bucket == 0 else policy).append(row)
    if any(len({r[1] for r in rows}) != 2 for rows in (training, calibration, policy, splits["test"])):
        raise ValueError("Both classes are required in each training/evaluation subset")
    started = time.perf_counter()
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2,
        max_features=150000, sublinear_tf=True, dtype=np.float32)
    features = [('characters', vectorizer)] if args.algorithm != 'hgb' else []
    baseline_hash = None
    if args.structural_features:
        from services.domain_features import hostname_structure
        features.append(('structure', make_pipeline(
            FunctionTransformer(hostname_structure, validate=False), StandardScaler())))
    if args.baseline_features:
        from services.domain_features import FrozenDomainMargin
        prior_manifest = json.loads((args.baseline_features / 'manifest.json').read_text(encoding='utf-8'))
        prior_path = args.baseline_features / 'classifier.joblib'
        baseline_hash = hashlib.sha256(prior_path.read_bytes()).hexdigest()
        if prior_manifest.get('feature_scope') != 'domain' or baseline_hash != prior_manifest.get('artifact_sha256'):
            raise ValueError('Prior model scope/checksum mismatch')
        prior = joblib.load(prior_path)
        features.append(('prior_margin', make_pipeline(FrozenDomainMargin(prior['pipeline']), StandardScaler())))
    if len(features) > 1:
        vectorizer = FeatureUnion(features)
    elif features:
        vectorizer = features[0][1]
    else:
        raise ValueError('Boosting requires structural and/or frozen prior features')
    train_x = vectorizer.fit_transform([r[0] for r in training])
    cal_x = vectorizer.transform([r[0] for r in calibration])
    policy_x = vectorizer.transform([r[0] for r in policy])
    counts = Counter(r[0] for r in calibration)
    candidates, best = [], None
    settings = args.max_leaves if args.algorithm == 'hgb' else args.c_values
    for regularization in settings:
        if args.algorithm == 'hgb':
            classifier = HistGradientBoostingClassifier(max_leaf_nodes=regularization, max_iter=180,
                learning_rate=0.08, min_samples_leaf=60, l2_regularization=3,
                class_weight='balanced', early_stopping=False, random_state=42)
        elif args.algorithm == 'svm':
            classifier = LinearSVC(C=regularization, dual='auto', max_iter=2000,
                class_weight='balanced', random_state=42)
        else:
            classifier = LogisticRegression(C=regularization, solver="liblinear", max_iter=500,
                class_weight="balanced", random_state=42)
        classifier.fit(train_x, [r[1] for r in training])
        # Calibrate on disjoint groups, weighting each host equally.
        candidate_calibrator = LogisticRegression(C=1, random_state=42)
        candidate_calibrator.fit(classifier.decision_function(cal_x).reshape(-1, 1),
            [r[1] for r in calibration], sample_weight=[1/counts[r[0]] for r in calibration])
        probabilities = candidate_calibrator.predict_proba(classifier.decision_function(policy_x).reshape(-1, 1))[:, 1]
        unique_rows, unique_prob = distinct_domain_labels(policy, probabilities)
        candidate_threshold = select_threshold(np.array([r[1] for r in unique_rows]), unique_prob, policy_budget)
        result = metrics(unique_rows, unique_prob, candidate_threshold)
        candidates.append({'max_leaf_nodes' if args.algorithm == 'hgb' else 'C': regularization,
            'threshold': candidate_threshold, 'policy': result})
        # Recall at the same conservative FPR budget; prefer fewer FP, then
        # stronger regularization when recall ties. No test scores used here.
        rank = (result['block_true_positives'], -result['block_false_positives'], -regularization)
        if best is None or rank > best[0]:
            best = (rank, classifier, candidate_calibrator, regularization)
        print(json.dumps({'validation_candidate': candidates[-1]}), flush=True)
    _, classifier, calibrator, regularization = best
    pipeline = make_pipeline(vectorizer, classifier)

    def predict(rows):
        margins = pipeline.decision_function([r[0] for r in rows]).reshape(-1, 1)
        return calibrator.predict_proba(margins)[:, 1]

    policy_prob = predict(policy)
    policy_domains, policy_domain_prob = distinct_domain_labels(policy, policy_prob)
    threshold = select_threshold(np.array([r[1] for r in policy_domains]), policy_domain_prob, policy_budget)
    # Evaluate full original holdout rows, including mixed-label domains.
    # Accuracy at 0.5 is descriptive, not the blocking policy's operating point.
    test_prob = predict(splits["test"])
    test_domains, test_domain_prob = distinct_domain_labels(splits["test"], test_prob)
    report = {"feature_scope": "domain", "seed": 42, "registered_domain_overlap": overlaps,
        "invalid_hostname_rows_rejected": {name: value[1] for name, value in loaded.items()},
        "training_unique_domains": len(training),
        "algorithm": args.algorithm, "selected_setting": regularization, "candidate_policy_validation": candidates,
        "prior_training_hosts_excluded": excluded_prior_groups,
        "structural_features": args.structural_features, "policy_fpr_budget": policy_budget,
        "frozen_prior_sha256": baseline_hash,
        "training_mixed_label_domains_excluded": sum(len(values) > 1 for values in labels.values()),
        "calibration_rows": len(calibration), "block_threshold": threshold,
        "fpr_budget": args.fpr_budget, "policy_validation": metrics(policy, policy_prob, threshold),
        "policy_unique_domain_labels": metrics(policy_domains, policy_domain_prob, threshold),
        "test": metrics(splits["test"], test_prob, threshold),
        "test_unique_domain_labels": metrics(test_domains, test_domain_prob, threshold),
        "training_seconds": time.perf_counter() - started,
        "dataset_sha256": {name: hashlib.sha256((args.dataset / f"{name}.csv").read_bytes()).hexdigest() for name in splits},
        "limitations": ["No TLS/content/path inspection", "No pornography category", "Row-level URL labels projected onto domain-only scores", "Holdout corpus is not a real-world traffic distribution"]}
    # Holdout is a release safety check, not a threshold-tuning source.
    eligible = threshold is not None and report["test_unique_domain_labels"]["block_fpr_95pct_upper"] <= args.fpr_budget
    report["enforcement_eligible"] = eligible
    if not eligible:
        report["release_note"] = "Candidate remains review-only: holdout FPR gate failed or no block threshold"
    args.output.mkdir(parents=True)
    artifact = args.output / "classifier.joblib"
    joblib.dump({"pipeline": pipeline, "calibrator": calibrator}, artifact, compress=3)
    report["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    version_bytes = artifact.read_bytes() + json.dumps({"block_threshold": threshold, "eligible": eligible}, sort_keys=True).encode()
    report["model_version"] = f"domain-{args.algorithm}-v4-" + hashlib.sha256(version_bytes).hexdigest()[:12]
    latency = []
    for host in [r[0] for r in splits["test"][:100]]:
        before = time.perf_counter()
        predict([(host, 0, host)])
        latency.append((time.perf_counter() - before) * 1000)
    report["cpu_inference_ms"] = {"p50": float(np.percentile(latency, 50)), "p95": float(np.percentile(latency, 95))}
    (args.output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
