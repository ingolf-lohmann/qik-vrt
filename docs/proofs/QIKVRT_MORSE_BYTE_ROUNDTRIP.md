# QIK-VRT Morse byte-roundtrip proof harness

Status: proposed reference harness; no independent remote endpoint or physical-channel experiment has yet been run.

For a finite byte string x, the target invariant is `decode(encode(x)) == x`. Frames must bind sequence, total frame count, chunk length, chunk SHA-256, and whole-payload SHA-256. The receiver rejects missing, duplicated, reordered, malformed, truncated, or digest-mismatched frames.

A successful local round-trip proves only that the tested reference implementation reconstructed those bytes. It does not prove physical-channel timing tolerance, external delivery, semantic equivalence, or downstream effects. `TRANSPORT_ACK != EFFECT_ACK`.

For repository-scale transfer, bind each artifact's path, mode, byte length, SHA-256, source commit/tree and chronology to an independently checked manifest. Morse is a low-throughput demonstration alphabet, not an appropriate bulk transport for a 438 MB repository.