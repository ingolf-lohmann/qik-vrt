<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Epistemic Status -00: reconciled v3 review candidate

Read CHANGE_NOTICE.md and SCOPE_RECONCILIATION.json first. The document name
remains -00 because this profile has not been submitted. This is an Experimental
individual Internet-Draft candidate, not an RFC or a consensus product.

The existing build.py and verify_staging.py paths are extended and reused.
Render with --write using the exact xml2rfc 3.34.0 19-package lock, then run
verify_staging.py --negative-controls. The observed Python patch is recorded;
the historical 3.12.13 full-runtime pin is not claimed as reproduced on 3.12.14.
SUBMISSION_MANIFEST.json, STAGING_RETURN_RECEIPT.json and SHA256SUMS bind the
candidate. The publisher action remains absent until exact human acceptance,
IETF contribution terms and the authenticated destination are established.
