"""Offline unit tests for the mandatory stable vulnerability gate."""
import unittest

from security_release_gate import gate, counts


class ReleaseSecurityGateTests(unittest.TestCase):
    def test_high_finding_blocks_stable_release(self):
        findings, allowed = gate({"Results": [
            {"Vulnerabilities": [{"VulnerabilityID": "CVE-TEST-1", "Severity": "HIGH"}]}
        ]})
        self.assertFalse(allowed)
        self.assertEqual(findings["HIGH"], 1)

    def test_critical_finding_blocks_stable_release(self):
        _, allowed = gate({"Results": [
            {"Vulnerabilities": [{"VulnerabilityID": "CVE-TEST-2", "Severity": "CRITICAL"}]}
        ]})
        self.assertFalse(allowed)

    def test_medium_only_not_release_approval(self):
        _, allowed = gate({"Results": [
            {"Vulnerabilities": [{"VulnerabilityID": "CVE-TEST-3", "Severity": "MEDIUM"}]}
        ]})
        self.assertTrue(allowed)

    def test_empty_report_results_must_be_explicit(self):
        self.assertTrue(gate({"Results": []})[1])
        with self.assertRaises(ValueError):
            counts({})
        with self.assertRaises(ValueError):
            counts({"Results": None})

    def test_malformed_vulnerability_fails_closed(self):
        with self.assertRaises(ValueError):
            gate({"Results": [{"Vulnerabilities": [{"Severity": "HIGH"}]}]})


if __name__ == "__main__":
    unittest.main()
