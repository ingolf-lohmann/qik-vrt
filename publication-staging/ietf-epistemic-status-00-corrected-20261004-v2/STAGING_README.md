# Corrected epistemic-status-00 successor

Staging only; not submitted. The original XML and v1 package remain unchanged.
The new XML is reconstructed from the predecessor by DERIVATION_MAP.json.
FORMAL_PROVED, empirical status, exact proposition, claim_scope, checked proof
and parent-bound refinements are now explicit. Evidence classes are not a rank.
RFC2119 and RFC8174 have normative xrefs; EFFECT_ACK-03 is informative work
in progress. Security Considerations preserves the security content.

Run build.py --xml2rfc <locked executable> --write or --check for two isolated
offline renders per format. The exact 19-package lock is required; all renderer
warnings and errors fail. CONTENT_VALIDATION.json records fresh semantic and
output checks. verify_staging.py checks all bytes, frozen closure, return
bindings, denied effects and altered-input controls.

Human author acceptance, contributor rights decision, governance and any later
submission decision are separate. No authorization is issued or consumed.
PREDECESSOR_EVIDENCE_TRANSFER=false.
