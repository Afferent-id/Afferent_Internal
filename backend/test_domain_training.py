"""Offline release-policy regressions; no network, training, or user database."""
import unittest

import numpy as np

from train_domain_model import distinct_domain_labels, select_threshold, upper_error


class ThresholdTests(unittest.TestCase):
    def test_ensemble_keeps_threshold_ties_and_does_not_call_a_network(self):
        from unittest.mock import Mock
        from services.domain_features import DomainRiskEnsemble, RiskScoreAdapter
        threshold = 0.9659728579361835
        models = []
        for score in (threshold, 0.90):
            pipeline, calibrator = Mock(), Mock()
            pipeline.decision_function.return_value = np.array([1.0])
            calibrator.predict_proba.return_value = np.array([[1 - score, score]])
            models.append({'pipeline': pipeline, 'calibrator': calibrator})
        risk = DomainRiskEnsemble(models).decision_function(['example.org'])
        self.assertEqual(RiskScoreAdapter().predict_proba(risk.reshape(-1, 1))[0, 1], threshold)
    def test_prior_feature_never_refits_the_frozen_classifier(self):
        from unittest.mock import Mock
        from services.domain_features import FrozenDomainMargin
        classifier = Mock()
        classifier.decision_function.return_value = np.array([0.4])
        feature = FrozenDomainMargin(classifier)
        self.assertIs(feature.fit(['example.org'], [0]), feature)
        np.testing.assert_array_equal(feature.transform(['example.org']), [[0.4]])
        classifier.fit.assert_not_called()
    def test_structure_is_finite_for_idna_empty_and_long_hosts(self):
        from services.domain_features import hostname_structure
        result = hostname_structure(['', 'example.org', 'xn--bcher-kva.de', 'a' * 63 + '.example.org'])
        self.assertEqual(result.shape, (4, 13))
        self.assertTrue(np.isfinite(result).all())
    def test_ties_cannot_hide_false_positives(self):
        y = np.array([0] * 2000 + [1] * 100)
        probabilities = np.array([0.1] * 1990 + [0.9] * 10 + [0.9] * 50 + [0.99] * 50)
        self.assertEqual(select_threshold(y, probabilities, 0.003), 0.99)

    def test_insufficient_negative_support_is_not_zero_risk(self):
        self.assertGreater(upper_error(0, 100), 0.003)
        self.assertIsNone(select_threshold(np.array([0, 1]), np.array([0.1, 0.99]), 0.003))

    def test_sorted_selection_matches_brute_force_across_tied_scores(self):
        rng = np.random.default_rng(42)
        for _ in range(10):
            y = np.r_[np.zeros(2000), np.ones(1000)]
            probabilities = np.round(rng.random(len(y)), 2)
            allowed = []
            for threshold in np.unique(probabilities):
                blocked = probabilities >= threshold
                fp = int(((y == 0) & blocked).sum())
                tp = int(((y == 1) & blocked).sum())
                if tp and upper_error(fp, 2000) <= 0.03:
                    allowed.append((tp, -fp, float(threshold)))
            expected = max(allowed)[2] if allowed else None
            self.assertEqual(select_threshold(y, probabilities, 0.03), expected)

    def test_domain_projection_keeps_conflicting_host_labels(self):
        rows = [('mixed.test', 0, 'mixed.test'), ('mixed.test', 1, 'mixed.test'), ('mixed.test', 1, 'mixed.test')]
        distinct, _ = distinct_domain_labels(rows, np.array([0.99, 0.99, 0.99]))
        self.assertEqual({row[1] for row in distinct}, {0, 1})
        self.assertEqual(len(distinct), 2)


if __name__ == '__main__':
    unittest.main()
