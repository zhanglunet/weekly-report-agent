#!/usr/bin/env python3
"""Regression tests for shared weekly-report-agent helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "weekly-report-agent" / "scripts"))

from common import redact_sensitive  # noqa: E402


class RedactionTests(unittest.TestCase):
    def test_redacts_shell_style_tokens(self) -> None:
        text = "access_token=abc refresh_token: secret tenant_access_token='tenant-secret'"
        result = redact_sensitive(text)
        self.assertNotIn("abc", result)
        self.assertNotIn("secret", result)
        self.assertNotIn("tenant-secret", result)
        self.assertIn("access_token=<redacted>", result)

    def test_redacts_json_style_tokens(self) -> None:
        text = '{"access_token": "abc", "appSecret": "secret"}'
        result = redact_sensitive(text)
        self.assertNotIn("abc", result)
        self.assertNotIn("secret", result)
        self.assertIn('"access_token": "<redacted>"', result)
        self.assertIn('"appSecret": "<redacted>"', result)

    def test_redacts_bearer_tokens(self) -> None:
        result = redact_sensitive("Authorization: Bearer xyz.123")
        self.assertEqual(result, "Authorization: Bearer <redacted>")


if __name__ == "__main__":
    unittest.main()
