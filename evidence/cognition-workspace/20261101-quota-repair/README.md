# Receiver quota repair

Ingolf Lohmann authorized implementation on 1 November 2026. The original local-Git/mesh cache is retained; no scheduler, replacement executor, credential export or new authority is introduced.

The existing receiver now reuses bounded public keys and immutable exact-commit source reads. Main before/after fences and the executing workflow run remain fresh. The existing D1 stores one atomic maximum quota stop shared across resource paths and isolates. A quota denial returns no raw provider body; suppressed requests explicitly report request_attempted=false. Cached keys expire after 60 seconds, immutable source after 600 seconds. This reduces a warm admission from six upstream reads to three without reusing a prior admission.

RECEIPT.json records exact Site source/version/deployment and three independent owner readbacks. The live sequence is 200, quota-denied 403, then 403 with request_attempted=false. The reset carried by the suppression is conservatively padded five seconds after the original provider reset. No new native intake is dispatched during that stop. Successful receiver publication is separate from a public manifest redownload (the client read returned HTTP403), source integration, native peer acceptance and product effects.

SOURCE.zip contains original selected Git bytes from receiver commit 1f2934e27dc8e91d6fdcf6f32a5afe862a91ce2b. CHECKS.zip retains original bounded test logs, bindings, own-work cache stage/idle results and the 32-update loopback measurement. These establish their named finite checks only. The own source batch is not an authenticated remote peer ACK.

Historical version8 acceptance retains its original cd05 Main/run identity. Native runtime/host/Claude duties, the unavailable admitted peer route, protected receiver GitHub read binding and R2 stop remain open. Productive EFFECT_ACK_DONE is false.

