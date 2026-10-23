"""
Train Stacker Meta-Learner (XGBoost) for AFFERENT.
Combines TF-IDF domain probabilities with lexical, structural, and Tranco reputation features.
Target: High recall under strict FPR budget (Wilson 95% CI <= 1%).
"""

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss

# Add project root and backend to sys.path
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from services.proxy_service import normalize_domain, ProxyError
from services.domain_features import DomainFeatureExtractor


def upper_error(count, total):
    """95% Wilson upper bound for false positive rate."""
    if total == 0:
        return 1.0
    z, p = 1.96, count / total
    return (p + z*z/(2*total) + z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))) / (1 + z*z/total)


def select_threshold(y, probabilities, budget):
    """Select threshold giving highest recall while respecting Wilson 95% CI FPR budget."""
    negatives = int((y == 0).sum())
    best = None
    for threshold in np.unique(probabilities):
        selected = probabilities >= threshold
        fp = int(((y == 0) & selected).sum())
        tp = int(((y == 1) & selected).sum())
        if tp and upper_error(fp, negatives) <= budget:
            candidate = (tp, -fp, float(threshold))
            if best is None or candidate > best:
                best = candidate
    return best[2] if best else None


def metrics(rows, probabilities, threshold):
    y = np.array([r[1] for r in rows])
    blocked = probabilities >= threshold if threshold is not None else np.zeros(len(y), dtype=bool)
    fp = int(((y == 0) & blocked).sum())
    tp = int(((y == 1) & blocked).sum())
    negatives = int((y == 0).sum())
    positives = int((y == 1).sum())
    
    return {
        "rows": len(rows),
        "unique_domains": len({r[0] for r in rows}),
        "benign": negatives,
        "malicious": positives,
        "binary_accuracy_at_0_5": float(accuracy_score(y, probabilities >= 0.5)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "block_false_positives": fp,
        "block_true_positives": tp,
        "block_fpr": fp / negatives if negatives else None,
        "block_fpr_95pct_upper": upper_error(fp, negatives),
        "block_precision": tp / (tp + fp) if tp + fp else None,
        "block_recall": tp / positives if positives else None,
        "unknown_fraction": float((~blocked & (probabilities > 0.1)).mean())
    }


def distinct_domain_labels(rows, probabilities):
    unique = {(r[0], r[1]): (r, float(p)) for r, p in zip(rows, probabilities)}
    return [v[0] for v in unique.values()], np.array([v[1] for v in unique.values()])


def load_dataset_rows(path):
    rows = []
    rejected = 0
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                host = normalize_domain(row["url"])
            except (ProxyError, ValueError):
                rejected += 1
                continue
            label = int(row["is_malicious"])
            registered = row.get("registered_domain", "").lower().rstrip(".") or host
            rows.append((host, label, registered))
    return rows, rejected


def extract_feature_matrix(rows, tfidf_predict_fn, extractor):
    """
    Build numerical feature matrix X for Stacker model.
    Feature vector schema (11 features):
    0: tfidf_prob
    1: length
    2: entropy
    3: subdomain_count
    4: hyphen_count
    5: digit_ratio
    6: vowel_ratio
    7: is_ip
    8: is_suspicious_tld
    9: tranco_feature
    10: is_tranco_top
    """
    # Batch predict TF-IDF
    tfidf_probs = tfidf_predict_fn(rows)
    
    X = np.zeros((len(rows), 11), dtype=np.float32)
    for i, (host, _, _) in enumerate(rows):
        feats = extractor.extract_features(host)
        X[i, 0] = tfidf_probs[i]
        X[i, 1] = feats["length"]
        X[i, 2] = feats["entropy"]
        X[i, 3] = feats["subdomain_count"]
        X[i, 4] = feats["hyphen_count"]
        X[i, 5] = feats["digit_ratio"]
        X[i, 6] = feats["vowel_ratio"]
        X[i, 7] = feats["is_ip"]
        X[i, 8] = feats["is_suspicious_tld"]
        X[i, 9] = feats["tranco_feature"]
        X[i, 10] = feats["is_tranco_top"]
        
    return X


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=project_root / "dataset" / "processed")
    parser.add_argument("--base-model", type=Path, default=backend_dir / "models" / "domain_v3" / "classifier.joblib")
    parser.add_argument("--tranco", type=Path, default=project_root / "dataset" / "raw" / "tranco" / "tranco_Y8YYG.csv")
    parser.add_argument("--output", type=Path, default=backend_dir / "models" / "stacker_v1")
    parser.add_argument("--fpr-budget", type=float, default=0.003)
    args = parser.parse_args()

    print(f"Loading Base TF-IDF model from: {args.base_model}")
    base_artifact = joblib.load(args.base_model)
    base_pipeline = base_artifact["pipeline"]
    base_calibrator = base_artifact["calibrator"]

    def base_predict(rows):
        margins = base_pipeline.decision_function([r[0] for r in rows]).reshape(-1, 1)
        return base_calibrator.predict_proba(margins)[:, 1]

    print("Initializing Domain Feature Extractor with Tranco list...")
    extractor = DomainFeatureExtractor(str(args.tranco) if args.tranco.exists() else None)

    print("Loading dataset splits (train, val, test)...")
    loaded = {name: load_dataset_rows(args.dataset / f"{name}.csv") for name in ("train", "val", "test")}
    splits = {name: value[0] for name, value in loaded.items()}

    # Group validation set into training for stacker and policy threshold evaluation
    labels = defaultdict(set)
    for host, label, _ in splits["train"]:
        labels[host].add(label)
    train_rows = [(host, next(iter(labels[host])), reg) for host, label, reg in splits["train"] if len(labels[host]) == 1]
    
    val_calib, val_policy = [], []
    for row in splits["val"]:
        bucket = int(hashlib.sha256(row[2].encode()).hexdigest()[:8], 16) % 2
        (val_calib if bucket == 0 else val_policy).append(row)

    print(f"Building feature matrices: Train={len(train_rows)}, ValCalib={len(val_calib)}, ValPolicy={len(val_policy)}, Test={len(splits['test'])}...")
    X_train = extract_feature_matrix(train_rows, base_predict, extractor)
    y_train = np.array([r[1] for r in train_rows], dtype=np.int32)

    X_val_calib = extract_feature_matrix(val_calib, base_predict, extractor)
    y_val_calib = np.array([r[1] for r in val_calib], dtype=np.int32)

    X_val_policy = extract_feature_matrix(val_policy, base_predict, extractor)
    y_val_policy = np.array([r[1] for r in val_policy], dtype=np.int32)

    X_test = extract_feature_matrix(splits["test"], base_predict, extractor)
    y_test = np.array([r[1] for r in splits["test"]], dtype=np.int32)

    print("Training XGBoost Stacker Meta-Learner...")
    started = time.perf_counter()
    stacker = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=4,
        eval_metric="logloss",
        random_state=42
    )
    # Train stacker on combined train and calibration data
    X_fit = np.vstack([X_train, X_val_calib])
    y_fit = np.concatenate([y_train, y_val_calib])
    stacker.fit(X_fit, y_fit)
    train_duration = time.perf_counter() - started

    # Evaluate on Policy set to find threshold
    policy_prob = stacker.predict_proba(X_val_policy)[:, 1]
    policy_domains, policy_domain_prob = distinct_domain_labels(val_policy, policy_prob)
    threshold = select_threshold(np.array([r[1] for r in policy_domains]), policy_domain_prob, args.fpr_budget)
    print(f"Optimal Policy Threshold for Wilson FPR <= {args.fpr_budget}: {threshold}")

    # Evaluate on Holdout Test set
    test_prob = stacker.predict_proba(X_test)[:, 1]
    test_domains, test_domain_prob = distinct_domain_labels(splits["test"], test_prob)

    report = {
        "model_type": "Stacker (XGBoost + TF-IDF Domain + Structural/Tranco Features)",
        "seed": 42,
        "feature_count": 11,
        "training_unique_domains": len(train_rows),
        "block_threshold": threshold,
        "fpr_budget": args.fpr_budget,
        "policy_validation": metrics(val_policy, policy_prob, threshold),
        "policy_unique_domain_labels": metrics(policy_domains, policy_domain_prob, threshold),
        "test": metrics(splits["test"], test_prob, threshold),
        "test_unique_domain_labels": metrics(test_domains, test_domain_prob, threshold),
        "training_seconds": train_duration,
    }

    eligible = threshold is not None and report["test_unique_domain_labels"]["block_fpr_95pct_upper"] <= args.fpr_budget
    report["enforcement_eligible"] = eligible
    if not eligible:
        report["release_note"] = "Candidate remains review-only: holdout FPR gate failed or no block threshold"

    # CPU Latency benchmark (single item inference)
    latencies = []
    sample_hosts = [r[0] for r in splits["test"][:100]]
    for host in sample_hosts:
        t0 = time.perf_counter()
        # Full inference path
        _ = extract_feature_matrix([(host, 0, host)], base_predict, extractor)
        latencies.append((time.perf_counter() - t0) * 1000)

    report["cpu_inference_ms"] = {
        "p50": float(np.percentile(latencies, 50)),
        "p95": float(np.percentile(latencies, 95))
    }

    # Save artifacts
    args.output.mkdir(parents=True, exist_ok=True)
    model_path = args.output / "stacker.joblib"
    joblib.dump({"stacker": stacker, "features": [
        "tfidf_prob", "length", "entropy", "subdomain_count", "hyphen_count",
        "digit_ratio", "vowel_ratio", "is_ip", "is_suspicious_tld", "tranco_feature", "is_tranco_top"
    ]}, model_path, compress=3)

    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    
    print("\n" + "="*60)
    print("TRAINING REPORT:")
    print(json.dumps(report, indent=2))
    print("="*60)
    print(f"Model saved to: {model_path}")


if __name__ == "__main__":
    main()
