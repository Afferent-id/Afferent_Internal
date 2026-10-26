"""Build a larger domain-only experiment from local snapshots; never visit URLs.

Frozen validation/test groups are excluded from new training. Novel groups have
a deterministic 70/20/10 train/validation/test assignment, before model fitting.
Category data is audited separately: gambling/adult are not malware labels.
"""
import argparse
import csv
import hashlib
import ipaddress
import json
from importlib.metadata import version
from collections import Counter, defaultdict
from pathlib import Path

import tldextract

from services.proxy_service import normalize_domain, ProxyError
from train_domain_model import load

EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


def group(host):
    return EXTRACT(host).top_domain_under_public_suffix or host


def split_group(value):
    bucket = int(hashlib.sha256(('reflex-domain-v4:' + value).encode()).hexdigest()[:8], 16) % 100
    return 'train' if bucket < 70 else 'val' if bucket < 90 else 'test'


def prepare(dataset, category_csv, output):
    if output.exists():
        raise ValueError('Do not overwrite frozen experiments')
    frozen = {name: load(dataset / 'processed' / (name + '.csv'))[0] for name in ('train', 'val', 'test')}
    frozen_groups = {name: {group(r[0]) for r in rows} for name, rows in frozen.items()}
    assert all(not frozen_groups[a] & frozen_groups[b] for a, b in (('train', 'val'), ('train', 'test'), ('val', 'test')))
    labels, sources = defaultdict(set), defaultdict(set)
    invalid, counts, hashes = Counter(), Counter(), {}
    for name in frozen:
        path = dataset / 'processed' / (name + '.csv')
        hashes[str(path.relative_to(dataset))] = hashlib.sha256(path.read_bytes()).hexdigest()

    def add(url, label, source):
        counts[source] += 1
        try:
            host = normalize_domain(url)
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                invalid['ip_only'] += 1
                return
            if '.' not in host:
                raise ValueError('single label')
        except (ProxyError, ValueError, UnicodeError):
            invalid[source] += 1
            return
        labels[host].add(label)
        sources[host].add(source)

    for name in ('train', 'test'):
        path = dataset / 'raw/grambeddings' / (name + '.csv')
        hashes[str(path.relative_to(dataset))] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8', newline='') as handle:
            for line in handle:
                label, sep, url = line.strip().partition(',')
                if sep and label in ('1', '2'):
                    add(url, int(label == '1'), 'grambeddings')
    path = dataset / 'raw/kaggle_malicious/malicious_phish.csv'
    hashes[str(path.relative_to(dataset))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            if row['type'] in ('benign', 'phishing', 'malware', 'defacement'):
                add(row['url'], int(row['type'] != 'benign'), 'kaggle')
    for host, label, _ in frozen['train']:
        add(host, label, 'frozen_train')

    reserved = frozen_groups['val'] | frozen_groups['test']
    splits = {name: [] for name in frozen}
    excluded = Counter()
    for host, values in sorted(labels.items()):
        registered = group(host)
        if registered in reserved:
            excluded['frozen_evaluation_group'] += 1
            continue
        split = 'train' if registered in frozen_groups['train'] else split_group(registered)
        # Mixed hosts cannot train a whole-host block, but BOTH labels must
        # remain in held-out evaluation so their false positives are counted.
        if len(values) != 1 and split == 'train':
            excluded['mixed_label_host'] += 1
            continue
        splits[split].extend((host, label, registered) for label in sorted(values))
    # Preserve all mixed labels in evaluation, not just convenient pure hosts.
    splits['val'].extend(frozen['val'])
    evaluation_groups = {name: {r[2] for r in rows} for name, rows in splits.items()}
    overlaps = {a + '/' + b: len(evaluation_groups[a] & evaluation_groups[b]) for a, b in (('train', 'val'), ('train', 'test'), ('val', 'test'))}
    assert not any(overlaps.values()), overlaps
    assert not evaluation_groups['train'] & frozen_groups['test']
    report = {'source_sha256': hashes, 'source_rows': dict(counts), 'invalid': dict(invalid),
        'tldextract_version': version('tldextract'), 'psl_source': 'bundled snapshot; network disabled',
        'excluded': dict(excluded), 'registered_domain_overlap': overlaps,
        'legacy_test_training_overlap': len(evaluation_groups['train'] & frozen_groups['test']),
        'split_seed': 'reflex-domain-v4', 'counts': {},
        'limitations': ['Historical URL labels projected to hosts, not current threat verification',
            'Fresh groups are from the same historical sources, not a temporal/external holdout',
            'Frozen validation is reused; legacy test is a regression set',
            'No category CSV, Tranco ranking, synthetic labels, LLM labels, paths or content used as training features']}
    if category_csv:
        category_labels = defaultdict(set)
        rejected = Counter()
        with category_csv.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                try:
                    host = normalize_domain(row['url'])
                except (ProxyError, ValueError, UnicodeError):
                    rejected['invalid'] += 1
                    continue
                category_labels[host].add(row['label'])
        report['category_audit'] = {'sha256': hashlib.sha256(category_csv.read_bytes()).hexdigest(),
            'unique_hosts': len(category_labels), 'mixed_labels': sum(len(v) > 1 for v in category_labels.values()),
            'pure_host_counts': dict(Counter(next(iter(v)) for v in category_labels.values() if len(v) == 1)),
            'rejected': dict(rejected), 'label_map': {'0': 'general', '1': 'gambling', '2': 'adult', '3': 'streaming_separate'},
            'used_for_training': False, 'reason': 'Category policy needs separate verified labels/evaluation; never label adult/gambling as phishing'}
    output.mkdir(parents=True)
    for name, rows in splits.items():
        with (output / (name + '.csv')).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['url', 'is_malicious', 'registered_domain'])
            writer.writerows(rows)
        report['counts'][name] = {'rows': len(rows), 'labels': dict(Counter(r[1] for r in rows)), 'groups': len(evaluation_groups[name])}
    (output / 'corpus_manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--category-csv', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.dataset, args.category_csv, args.output)
