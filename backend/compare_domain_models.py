"""Offline release comparison, with the actual generated-host abstention policy.

Run AFTER selection on validation. Never tune a threshold with these results.
This does not fetch any domain or alter proxy/database policy.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np

from services.domain_scanner import generated_hostname
from train_domain_model import distinct_domain_labels, load, metrics

SENTINELS = ('microsoft.com', 'www.microsoft.com', 'google.com', 'www.google.com',
    'youtube.com', 'www.youtube.com', 'facebook.com', 'www.facebook.com',
    'github.com', 'api.github.com', 'chatgpt.com', 'openai.com', 'wikipedia.org',
    'neverssl.com', 'cloudflare.com', 'login.microsoftonline.com')


def artifact(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    path = directory / 'classifier.joblib'
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['artifact_sha256']:
        raise ValueError('Untrusted artifact checksum')
    return joblib.load(path), manifest


def score(model, hosts):
    return model['calibrator'].predict_proba(model['pipeline'].decision_function(hosts).reshape(-1, 1))[:, 1]


def evaluate(model, manifest, rows):
    probabilities = score(model, [row[0] for row in rows])
    unique, probabilities = distinct_domain_labels(rows, probabilities)
    # A guard abstention is UNKNOWN, regardless of the lexical probability.
    guarded = np.array([generated_hostname(row[0]) for row in unique])
    effective = probabilities.copy()
    effective[guarded] = 0.5
    # Measure the candidate's PROPOSED operating point even when its release
    # flag is false. A rejected candidate must not appear to have zero FP.
    threshold = manifest['block_threshold']
    result = metrics(unique, effective, threshold)
    result['generated_hostname_abstentions'] = int(guarded.sum())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--fresh', type=Path, required=True)
    parser.add_argument('--legacy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Never overwrite a recorded release comparison')
    sets = {'fresh_same_source_test': load(args.fresh / 'test.csv')[0], 'legacy_reused_test': load(args.legacy / 'test.csv')[0]}
    report = {'limitations': ['Fresh domain groups are from historical sources, not a temporal/external holdout',
        'Legacy test has been reused; no threshold selection used either test',
        'Sentinels are regression checks, not proof that domain content is safe',
        'Warm inference timing excludes proxy/network/database; category CSV not trained'], 'models': {}}
    for name, directory in (('baseline', args.baseline), ('candidate', args.candidate)):
        model, manifest = artifact(directory)
        results = {key: evaluate(model, manifest, rows) for key, rows in sets.items()}
        probabilities = score(model, list(SENTINELS))
        threshold = manifest['block_threshold']
        results['sentinel_blocked'] = [host for host, p in zip(SENTINELS, probabilities)
            if threshold is not None and p >= threshold and manifest['enforcement_eligible']]
        times = []
        for host, _, _ in sets['fresh_same_source_test'][:500]:
            started = time.perf_counter()
            score(model, [host])
            times.append((time.perf_counter() - started) * 1000)
        results['warm_inference_ms'] = {'p50': float(np.percentile(times, 50)), 'p95': float(np.percentile(times, 95))}
        results['model_version'] = manifest['model_version']
        results['artifact_bytes'] = (directory / 'classifier.joblib').stat().st_size
        report['models'][name] = results
    baseline, candidate = report['models']['baseline'], report['models']['candidate']
    budget = 0.003
    report['release_gates'] = {
        'artifact_enforcement_eligible': artifact(args.candidate)[1]['enforcement_eligible'],
        'fresh_fpr_95_upper_within_budget': candidate['fresh_same_source_test']['block_fpr_95pct_upper'] <= budget,
        'legacy_fpr_95_upper_within_budget': candidate['legacy_reused_test']['block_fpr_95pct_upper'] <= budget,
        'fresh_recall_improved': candidate['fresh_same_source_test']['block_recall'] > baseline['fresh_same_source_test']['block_recall'],
        'legacy_recall_not_regressed': candidate['legacy_reused_test']['block_recall'] >= baseline['legacy_reused_test']['block_recall'],
        'sentinels_not_blocked': not candidate['sentinel_blocked'],
        'warm_p95_under_10ms': candidate['warm_inference_ms']['p95'] < 10,
        'artifact_under_10MiB': candidate['artifact_bytes'] < 10 * 1024 * 1024,
    }
    report['promotable'] = all(report['release_gates'].values())
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
