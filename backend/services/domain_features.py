"""Pure hostname structure for offline-trained ML; no lists, DNS or content."""
import math
from collections import Counter

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class FrozenDomainMargin(TransformerMixin, BaseEstimator):
    """Reuse a trusted prior classifier as one feature; never refit its weights."""
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def fit(self, hosts, y=None):
        return self

    def transform(self, hosts):
        return self.pipeline.decision_function(hosts).reshape(-1, 1)


class DomainRiskEnsemble:
    """Conservative max-risk voting. Output is a score, not a joint posterior."""
    def __init__(self, members):
        self.members = members

    def decision_function(self, hosts):
        probabilities = [model['calibrator'].predict_proba(
            model['pipeline'].decision_function(hosts).reshape(-1, 1))[:, 1]
            for model in self.members]
        # Return the score directly: logit/sigmoid round trips could move a
        # score tied exactly at an existing blocking threshold below it.
        return np.max(probabilities, axis=0)


class RiskScoreAdapter:
    """Preserve the existing inference interface without claiming calibration."""
    def predict_proba(self, margins):
        score = np.clip(np.asarray(margins).reshape(-1), 0, 1)
        return np.column_stack([1 - score, score])


def hostname_structure(hosts):
    values = []
    for host in hosts:
        labels = host.split('.')
        main = labels[-2] if len(labels) > 1 else host
        counts = Counter(host)
        entropy = -sum((n / len(host)) * math.log2(n / len(host)) for n in counts.values()) if host else 0
        digits = sum(char.isdigit() for char in host)
        hyphens = host.count('-')
        values.append([len(host), len(labels), max(map(len, labels)), len(main),
            len(labels[-1]), digits, digits / max(1, len(host)), hyphens,
            hyphens / max(1, len(host)), entropy,
            sum(char in 'aeiou' for char in main) / max(1, len(main)),
            int(main.startswith('xn--')), len(set(host)) / max(1, len(host))])
    return np.asarray(values, dtype=np.float32)
