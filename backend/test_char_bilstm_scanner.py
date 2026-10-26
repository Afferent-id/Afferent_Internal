"""Unit and integration tests for Char-BiLSTM URL scanner."""

import os
import unittest

os.environ["SERVICE_API_KEY"] = "test-service-key-bilstm"
os.environ["DEV_BYPASS_AUTH"] = "false"

from app import app
import char_bilstm_scanner


class TestCharBiLSTMScanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Other discovered modules set their own service credentials at import.
        os.environ["SERVICE_API_KEY"] = "test-service-key-bilstm"
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.headers = {"Authorization": "Bearer test-service-key-bilstm"}

    def test_01_scanner_is_available(self):
        self.assertTrue(char_bilstm_scanner.is_scanner_available(), "Char-BiLSTM scanner should be available")

    def test_02_benign_url_classification(self):
        result = char_bilstm_scanner.scan_url_dl("https://kominfo.go.id")
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "clean")
        self.assertEqual(result["action"], "ALLOW")
        self.assertIn("benign", result["probabilities"])
        self.assertGreater(result["probabilities"]["benign"], 0.5)

    def test_03_phishing_url_classification(self):
        result = char_bilstm_scanner.scan_url_dl("http://bca-klik-secure-auth.xyz/verify")
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "malicious")
        self.assertEqual(result["action"], "BLOCK")
        self.assertEqual(result["severity"], "high")
        self.assertGreaterEqual(result["p_malicious"], 0.90)

    def test_04_judol_url_classification(self):
        result = char_bilstm_scanner.scan_url_dl("http://slot-gacor-olympus-maxwin.xyz/login")
        self.assertIsNotNone(result)
        self.assertEqual(result["verdict"], "malicious")
        self.assertEqual(result["action"], "BLOCK")
        self.assertEqual(result["threat_type"], "judol_scam")

    def test_05_api_endpoint_scan_dl(self):
        res = self.client.post(
            "/api/threat/scan-dl",
            json={"url": "http://paypal-verification-account-update.xyz/login"},
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["verdict"], "malicious")
        self.assertEqual(data["data"]["action"], "BLOCK")

    def test_06_retired_unified_endpoint_does_not_run_analysis(self):
        from unittest.mock import patch
        # Employee reports and provider-only checks use separate authenticated APIs.
        with patch("integrations.scan_virustotal") as vt, \
             patch("integrations.scan_urlscan") as urlscan, \
             patch("char_bilstm_scanner.scan_url_dl") as model:
            res = self.client.post(
                "/api/threat/analyze",
                json={"indicator": "http://slot-gacor-maxwin-jp.vip/login"},
                headers=self.headers
            )
            self.assertEqual(res.status_code, 410)
            self.assertIn("error", res.get_json())
            vt.assert_not_called()
            urlscan.assert_not_called()
            model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
