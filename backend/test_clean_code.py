"""Offline characterization checks for cache, pseudonyms and SOC baselines.

Uses a disposable SQLite file; never initializes or changes the application's DB.
"""
import copy
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import ai_anonymizer
import ai_cache
from services.behavior_service import heatmap


class TrackedConnection(sqlite3.Connection):
    def close(self):
        self.was_closed = True
        super().close()


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='afferent-cache-check-')
        self.db_path = Path(self.directory.name) / 'cache.sqlite'
        self.connections = []

        def connect():
            connection = sqlite3.connect(self.db_path, factory=TrackedConnection)
            connection.row_factory = sqlite3.Row
            connection.was_closed = False
            self.connections.append(connection)
            return connection

        self.connection_patch = patch.object(ai_cache.database, 'get_connection', connect)
        self.connection_patch.start()
        ai_cache.init_cache_table()

    def tearDown(self):
        self.connection_patch.stop()
        try:
            self.assertTrue(all(connection.was_closed for connection in self.connections))
        finally:
            for connection in self.connections:
                if not connection.was_closed:
                    connection.close()
            self.directory.cleanup()

    def execute(self, sql, values=()):
        with closing(sqlite3.connect(self.db_path)) as connection, connection:
            return connection.execute(sql, values).fetchall()

    def test_initialization_is_idempotent(self):
        ai_cache.set_cache('existing', {'value': 1})
        ai_cache.init_cache_table()
        self.assertEqual(ai_cache.get_cached('existing'), {'value': 1})

    def test_missing_entry(self):
        self.assertIsNone(ai_cache.get_cached('missing'))

    def test_round_trip_unicode_and_nested_data(self):
        payload = {'reason': 'éducation', 'nested': [1, None, {'enabled': True}]}
        ai_cache.set_cache('unicode', payload)
        self.assertEqual(ai_cache.get_cached('unicode'), payload)

    def test_upsert_replaces_value(self):
        ai_cache.set_cache('same', {'value': 1})
        ai_cache.set_cache('same', {'value': 2})
        self.assertEqual(ai_cache.get_cached('same'), {'value': 2})
        self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 1)

    def test_expired_entry_is_deleted(self):
        ai_cache.set_cache('expired', {}, ttl_seconds=-10)
        self.assertIsNone(ai_cache.get_cached('expired'))
        self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 0)

    def test_expiry_boundary_keeps_existing_semantics(self):
        now = datetime(2026, 10, 11, 12, 0)
        with patch.object(ai_cache, 'datetime') as clock:
            clock.utcnow.return_value = now
            clock.fromisoformat.side_effect = datetime.fromisoformat
            ai_cache.set_cache('boundary', {'value': 1}, ttl_seconds=0)
            self.assertEqual(ai_cache.get_cached('boundary'), {'value': 1})
            # Reads use >; statistics use SQL >. Do not silently change this API.
            self.assertEqual(ai_cache.get_cache_stats(),
                             {'total_entries': 1, 'valid_entries': 0, 'expired': 1})
            ai_cache.cleanup_expired()
            self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 1)

    def test_corrupt_json_returns_none_without_deleting_row(self):
        ai_cache.set_cache('broken', {})
        self.execute('UPDATE ai_cache SET result_json = ? WHERE cache_key = ?', ('{', 'broken'))
        self.assertIsNone(ai_cache.get_cached('broken'))
        self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 1)

    def test_corrupt_timestamp_still_raises(self):
        ai_cache.set_cache('broken', {})
        self.execute('UPDATE ai_cache SET expires_at = ? WHERE cache_key = ?', ('invalid', 'broken'))
        with self.assertRaises(ValueError):
            ai_cache.get_cached('broken')

    def test_cleanup_only_removes_expired_entries(self):
        ai_cache.set_cache('expired', {}, ttl_seconds=-10)
        ai_cache.set_cache('valid', {})
        self.assertEqual(ai_cache.get_cache_stats(),
                         {'total_entries': 2, 'valid_entries': 1, 'expired': 1})
        ai_cache.cleanup_expired()
        self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 1)
        self.assertEqual(ai_cache.get_cached('valid'), {})

    def test_invalidate_one_and_all(self):
        for key in ('one', 'two'):
            ai_cache.set_cache(key, {})
        ai_cache.invalidate('one')
        ai_cache.invalidate('missing')
        self.assertIsNone(ai_cache.get_cached('one'))
        self.assertEqual(ai_cache.get_cached('two'), {})
        ai_cache.invalidate_all()
        self.assertEqual(ai_cache.get_cache_stats()['total_entries'], 0)

    def test_serialization_error_opens_no_connection(self):
        previous_count = len(self.connections)
        with self.assertRaises(TypeError):
            ai_cache.set_cache('invalid', {'value': object()})
        self.assertEqual(len(self.connections), previous_count)

    def test_sql_error_is_propagated_and_connection_closed(self):
        self.execute('DROP TABLE ai_cache')
        with self.assertRaises(sqlite3.OperationalError):
            ai_cache.set_cache('failure', {})
        self.assertTrue(self.connections[-1].was_closed)


class AnonymizerTests(unittest.TestCase):
    def test_email_normalization_and_unknown(self):
        self.assertEqual(ai_anonymizer.anonymize_email(' EMPLOYEE@EXAMPLE.COM '),
                         ai_anonymizer.anonymize_email('employee@example.com'))
        self.assertEqual(ai_anonymizer.anonymize_email(None), 'EMP-UNKNOWN')
        self.assertEqual(ai_anonymizer.anonymize_email(''), 'EMP-UNKNOWN')

    def test_batch_is_deep_copy_and_collision_mapping_is_last_email(self):
        users = [{'email': 'employee@example.com', 'details': [1]},
                 {'email': ' EMPLOYEE@example.com ', 'details': [2]}, {'points': 0}]
        original = copy.deepcopy(users)
        anonymous, mapping = ai_anonymizer.anonymize_user_summary_list(users)
        self.assertEqual(users, original)
        self.assertEqual(anonymous[0]['email'], anonymous[1]['email'])
        self.assertEqual(mapping[anonymous[0]['email']], users[1]['email'])
        self.assertEqual(mapping['EMP-UNKNOWN'], '')
        anonymous[0]['details'].append(3)
        self.assertEqual(users, original)

    def test_single_user_preserves_raw_email_and_nested_values(self):
        context = {'email': 'employee@example.com', 'nested': {'points': 50}}
        anonymous, raw_email = ai_anonymizer.anonymize_user_context(context)
        self.assertEqual(raw_email, context['email'])
        anonymous['nested']['points'] = 0
        self.assertEqual(context['nested']['points'], 50)

    def test_organization_uses_same_batch_contract(self):
        users = [{'email': 'employee@example.com', 'details': []}, {'points': 0}]
        context = {'chronic_risk_users': users, 'summary': {'value': 1}}
        original = copy.deepcopy(context)
        anonymous, mapping = ai_anonymizer.anonymize_org_context(context)
        expected_users, expected_mapping = ai_anonymizer.anonymize_user_summary_list(users)
        self.assertEqual(anonymous['chronic_risk_users'], expected_users)
        self.assertEqual(mapping, expected_mapping)
        anonymous['summary']['value'] = 2
        anonymous['chronic_risk_users'][0]['details'].append(1)
        self.assertEqual(context, original)

    def test_non_list_organization_field_is_preserved(self):
        for value in (None, {}, 'unknown'):
            with self.subTest(value=value):
                self.assertEqual(ai_anonymizer.anonymize_org_context({'chronic_risk_users': value}),
                                 ({'chronic_risk_users': value}, {}))
        self.assertEqual(ai_anonymizer.anonymize_org_context({}), ({}, {}))

    def test_restore_mutates_only_supported_fields_in_place(self):
        result = {'classifications': [{'email': 'EMP-1'}, {'email': 'unmapped'}],
                  'chronic_risk_users': [{'email': 'EMP-1'}],
                  'other': [{'email': 'EMP-1'}]}
        restored = ai_anonymizer.deanonymize_response(result, {'EMP-1': 'employee@example.com'})
        self.assertIs(restored, result)
        self.assertEqual(result['classifications'][0]['email'], 'employee@example.com')
        self.assertEqual(result['classifications'][1]['email'], 'unmapped')
        self.assertEqual(result['chronic_risk_users'][0]['email'], 'employee@example.com')
        self.assertEqual(result['other'][0]['email'], 'EMP-1')

    def test_restore_string_non_dict_and_non_list(self):
        result = {'email': 'EMP-1'}
        self.assertIs(ai_anonymizer.deanonymize_response(result, 'employee@example.com'), result)
        self.assertEqual(result['email'], 'employee@example.com')
        values = [{'classifications': None}, [], None, 'raw']
        for value in values:
            self.assertIs(ai_anonymizer.deanonymize_response(value, {}), value)

    def test_malformed_list_entry_keeps_error_contract(self):
        with self.assertRaises(AttributeError):
            ai_anonymizer.deanonymize_response({'classifications': [None]}, {})


class HeatmapTests(unittest.TestCase):
    def user(self, points, clicks=0, **extra):
        return {'email': 'employee@example.com', 'points': points, 'click_count': clicks, **extra}

    def test_risk_boundaries_and_click_override(self):
        for points, clicks, expected in [(59, 0, 'DANGER'), (60, 0, 'VULNERABLE'),
                                         (129, 0, 'VULNERABLE'), (130, 1, 'SAFE'),
                                         (130, 2, 'VULNERABLE'), (200, 4, 'DANGER')]:
            with self.subTest(points=points, clicks=clicks):
                result = heatmap([self.user(points, clicks)])['classifications'][0]
                self.assertEqual(result['risk_level'], expected)

    def test_input_coercion_and_clamped_score(self):
        for points, clicks, expected_score in [(None, None, 100), ('130', '0', 35),
                                                (-50, 0, 100), (300, 0, 0)]:
            with self.subTest(points=points):
                result = heatmap([self.user(points, clicks)])['classifications'][0]
                self.assertEqual(result['risk_score'], expected_score)
                self.assertEqual(result['divisi'], 'General')

    def test_summary_counts_ties_and_determinism(self):
        users = [self.user(10, divisi='IT'), self.user(10, divisi='Finance'),
                 self.user(100), self.user(180)]
        original = copy.deepcopy(users)
        result = heatmap(users)
        self.assertEqual(result, heatmap(users))
        self.assertEqual(users, original)
        summary = result['org_risk_summary']
        self.assertEqual((summary['danger_count'], summary['vulnerable_count'], summary['safe_count']),
                         (2, 1, 1))
        self.assertEqual(summary['most_at_risk_division'], 'IT')
        self.assertEqual(result['_source'], 'behavior_rules')

    def test_empty_and_invalid_inputs(self):
        self.assertEqual(heatmap([])['org_risk_summary']['most_at_risk_division'], '-')
        with self.assertRaises(KeyError):
            heatmap([{'points': 100}])
        with self.assertRaises(ValueError):
            heatmap([self.user('not-a-score')])


if __name__ == '__main__':
    unittest.main()
