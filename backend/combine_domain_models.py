"""Evaluate a fixed conservative ensemble rule, not another test-tuned threshold.

Maximum member risk, at the highest pre-existing member blocking threshold.
The output is explicitly a risk score, not a calibrated joint probability.
No fitting or threshold search is performed here. All test sets are reported
as reused development/regression evidence, not independent future performance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import joblib

from compare_domain_models import artifact, evaluate
from services.domain_features import DomainRiskEnsemble, RiskScoreAdapter
from train_domain_model import load


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--challenger', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Never overwrite evaluated artifacts')
    members = [artifact(directory) for directory in (args.baseline, args.challenger)]
    if not all(manifest['enforcement_eligible'] for _, manifest in members):
        raise ValueError('Only individually safety-qualified member artifacts may be considered')
    threshold = max(manifest['block_threshold'] for _, manifest in members)
    model = {'pipeline': DomainRiskEnsemble([value[0] for value in members]), 'calibrator': RiskScoreAdapter()}
    manifest = {'feature_scope': 'domain', 'algorithm': 'conservative_max_risk_ensemble',
        'score_label': 'ensemble risk score', 'score_semantics': 'Maximum of member scores; not a calibrated joint probability',
        'members': [{'model_version': m['model_version'], 'artifact_sha256': m['artifact_sha256'],
            'threshold': m['block_threshold']} for _, m in members],
        'block_threshold': threshold, 'threshold_selection': 'Fixed highest member threshold; no fitting/search/test tuning',
        'fpr_budget': 0.003, 'enforcement_eligible': True,
        'limitations': ['Development/reused historical corpus, not untouched external or temporal validation',
            'No TLS/content/path inspection; no adult/gambling category training',
            'Unknown is retained; scores are evidence and SOC policies remain authoritative']}
    for name in ('val', 'test'):
        rows, _ = load(args.dataset / (name + '.csv'))
        manifest[name + '_unique_domain_labels'] = evaluate(model, manifest, rows)
    manifest['enforcement_eligible'] = all(manifest[name + '_unique_domain_labels']['block_fpr_95pct_upper'] <= 0.003 for name in ('val', 'test'))
    args.output.mkdir(parents=True)
    path = args.output / 'classifier.joblib'
    joblib.dump(model, path, compress=3)
    manifest['artifact_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest['model_version'] = 'domain-ensemble-v4-' + hashlib.sha256(path.read_bytes() + str(threshold).encode()).hexdigest()[:12]
    manifest['dataset_sha256'] = {name: hashlib.sha256((args.dataset / (name + '.csv')).read_bytes()).hexdigest() for name in ('train', 'val', 'test')}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    main()
