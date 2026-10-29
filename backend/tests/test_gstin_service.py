"""
Automated tests for services/gstin_service.py

Run from the backend folder:
    python -m unittest discover -s tests -v

No database, network or API keys are needed — the GSTIN validation
logic is pure Python.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.gstin_service import (
    run_gstin_checks,
    validate_gstin_format,
    validate_gstin_checksum,
    validate_state_match,
)

UP_ADDRESS = "12, Begum Bridge Road, Meerut, Uttar Pradesh - 250001"
MH_ADDRESS = "88, Andheri West, Mumbai, Maharashtra - 400053"


class TestFormat(unittest.TestCase):
    def test_valid_format(self):
        r = validate_gstin_format("09ABCDE1234F1ZY")
        self.assertTrue(r["valid"])
        self.assertEqual(r["state_name"], "Uttar Pradesh")

    def test_short_gstin_is_critical(self):
        r = validate_gstin_format("07XYZ12345")
        self.assertFalse(r["valid"])
        self.assertEqual(r["risk"], "CRITICAL")

    def test_empty_gstin_is_critical(self):
        r = validate_gstin_format("")
        self.assertFalse(r["valid"])
        self.assertEqual(r["risk"], "CRITICAL")

    def test_unknown_state_code_is_critical(self):
        r = validate_gstin_format("99ABCDE1234F1Z5")
        self.assertFalse(r["valid"])
        self.assertEqual(r["risk"], "CRITICAL")


class TestChecksum(unittest.TestCase):
    def test_demo_gstin_checksum_valid(self):
        # Checksum character computed with the real Luhn Mod-36 algorithm
        self.assertTrue(validate_gstin_checksum("09ABCDE1234F1ZY")["valid"])

    def test_real_world_gstin_checksum_valid(self):
        # Central Warehousing Corporation — a real, registered GSTIN
        self.assertTrue(validate_gstin_checksum("33AAACC1206D1ZN")["valid"])

    def test_wrong_last_char_fails(self):
        r = validate_gstin_checksum("09ABCDE1234F1ZX")
        self.assertFalse(r["valid"])
        self.assertEqual(r["risk"], "HIGH")


class TestStateMatch(unittest.TestCase):
    def test_matching_state(self):
        r = validate_state_match("09ABCDE1234F1ZY", UP_ADDRESS)
        self.assertEqual(r["risk"], "NONE")

    def test_mismatch_is_high(self):
        r = validate_state_match("09PQRST6789K1ZU", MH_ADDRESS)
        self.assertEqual(r["risk"], "HIGH")

    def test_missing_address_is_medium(self):
        r = validate_state_match("09ABCDE1234F1ZY", "")
        self.assertEqual(r["risk"], "MEDIUM")


class TestRouting(unittest.TestCase):
    """End-to-end routing decisions, exactly as invoice_router uses them."""

    def test_clean_invoice_auto_approves_with_zero_score(self):
        r = run_gstin_checks("09ABCDE1234F1ZY", UP_ADDRESS)
        ra = r["risk_assessment"]
        self.assertEqual(ra["score"], 0)
        self.assertEqual(ra["level"], "NONE")
        self.assertEqual(ra["action"], "AUTO_APPROVE")

    def test_state_mismatch_goes_to_manual_review(self):
        r = run_gstin_checks("09PQRST6789K1ZU", MH_ADDRESS)
        ra = r["risk_assessment"]
        self.assertEqual(ra["score"], 25)
        self.assertEqual(ra["action"], "MANUAL_REVIEW")

    def test_invalid_format_is_blocked(self):
        r = run_gstin_checks("07XYZ12345", "Karol Bagh, New Delhi, Delhi")
        ra = r["risk_assessment"]
        self.assertEqual(ra["level"], "CRITICAL")
        self.assertEqual(ra["action"], "BLOCK")

    def test_checksum_failure_goes_to_manual_review(self):
        r = run_gstin_checks("09ABCDE1234F1ZX", UP_ADDRESS)
        ra = r["risk_assessment"]
        self.assertEqual(ra["score"], 25)
        self.assertEqual(ra["action"], "MANUAL_REVIEW")


if __name__ == "__main__":
    unittest.main()
