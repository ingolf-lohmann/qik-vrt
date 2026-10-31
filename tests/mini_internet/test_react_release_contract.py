"""Static fail-closed contract checks for imported mini-internet React fixture.

These are source guards, not browser execution or production attestation.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).parent / "web" / "app.jsx"


class ReactReleaseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_ecdsa_p256_signature_is_checked_before_asset_fetch(self):
        src = self.source
        self.assertIn('namedCurve: "P-256"', src)
        self.assertIn('crypto.subtle.verify', src)
        self.assertIn('RELEASE_SIGNATURE_INVALID', src)
        self.assertLess(src.index('crypto.subtle.verify'), src.index('fetch(m.asset'))

    def test_digest_verified_before_payload_consumption(self):
        src = self.source
        self.assertIn('crypto.subtle.digest("SHA-256", bytes)', src)
        self.assertIn('RELEASE_HASH_MISMATCH', src)
        self.assertLess(src.index('RELEASE_HASH_MISMATCH'), src.index('JSON.parse(new TextDecoder().decode(bytes))'))

    def test_no_second_asset_fetch_or_reload(self):
        src = self.source
        self.assertEqual(len(re.findall(r'fetch\(m\.asset\b', src)), 1)
        self.assertNotRegex(src, r'location\s*\.\s*(reload|assign|replace)\s*\(')
        self.assertNotIn('window.location =', src)

    def test_activation_follows_verification(self):
        src = self.source
        self.assertLess(src.index('await verifyRelease('), src.index('fetch("/activated"'))
        self.assertIn('fetch("/rejected"', src)

    def test_activation_receipt_precedes_visible_success(self):
        src = self.source
        self.assertIn('RELEASE_ACTIVATION_RECEIPT_INVALID', src)
        self.assertIn('RELEASE_ACTIVATION_HTTP_', src)
        self.assertIn('fetch("/readback/active"', src)
        self.assertLess(src.index('if (!Array.isArray(readback.activated)'), src.index('seen.current.add(rel.version)'))
        self.assertLess(src.index('seen.current.add(rel.version)'), src.index('setRelease(v)'))

    def test_bootstrap_key_is_not_yet_pinned(self):
        # Deliberate negative control: do not silently claim trusted bootstrap.
        self.assertIn('window.__QIKVRT_RELEASE_KEY__', self.source)


if __name__ == "__main__":
    unittest.main()
