# QIK-VRT licensing guide

Copyright (c) 2026 Ingolf Lohmann.

## Controlling order

Licensing is resolved in this order:

1. a third-party license or provenance notice;
2. an explicit file-level SPDX identifier or specific notice;
3. the current QIK-VRT software rule;
4. the current QIK-VRT non-source rule.

## Current QIK-VRT source code

QIK-VRT-controlled source code and executable tooling identified as
`PolyForm-Noncommercial-1.0.0` are licensed under the PolyForm Noncommercial
License 1.0.0. The unmodified standard text is
[`LICENSES/PolyForm-Noncommercial-1.0.0.txt`](LICENSES/PolyForm-Noncommercial-1.0.0.txt).

The standard public license permits use, change, and distribution only for its
permitted noncommercial purposes. Ordinary commercial use is not part of that
grant. Commercial exploitation, commercial SaaS or platform operation,
commercial integration, resale, and other anticipated commercial applications
require a separate written license from the rights holder unless a statutory
exception applies.

PolyForm Noncommercial is source-available but is not an OSI-approved
open-source license. Its special permissions for the organizations and uses
named in the standard text remain fully applicable.

Required Notice: Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.

## Documentation and non-source content

QIK-VRT documentation and other non-source material identified as
`CC-BY-NC-ND-4.0` are licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International. Its legal code is
[`LICENSES/CC-BY-NC-ND-4.0.txt`](LICENSES/CC-BY-NC-ND-4.0.txt).

That license requires attribution when licensed material is shared, limits the
grant to NonCommercial purposes, and does not permit sharing Adapted Material
under the license. Statutory exceptions and limitations are unaffected.

## Historical Apache-2.0 boundary

The change is prospective. The baseline commit
`8ae1884116221087bdcc75eed9905bb80bdd9e95`, earlier releases, and any file
validly received under Apache-2.0 retain the Apache-2.0 grant attached to that
version or file. Those rights cannot be retroactively narrowed by replacing a
later repository license file. `LICENSES/Apache-2.0.txt` is retained for that
boundary and for any specifically marked component; it is not the current
default for newly licensed QIK-VRT software.

## Third-party and contribution boundary

Third-party software, bundled runtimes, standards material, and dependencies
remain under their own licenses. No QIK-VRT classification relicenses them.
The new default applies only to material for which the named licensor holds the
necessary rights. Future contributions require the written rights arrangement
described in [CONTRIBUTING.md](CONTRIBUTING.md).

## Commercial agreements and marks

A separate written agreement may grant commercial software rights and may
also address trademarks, certification, endorsement, managed hosting,
integration, support, consulting, training, warranties, indemnities, or
service levels. No such right arises from repository access, an operational
authorization, a test result, correspondence, or silence.

## Operational authorization is separate

The authorization gate before a network write, release, payment, or other
external effect records operator authority and responsibility for that effect.
It neither expands nor replaces the applicable copyright license.

See [LICENSE_TRANSITION.md](LICENSE_TRANSITION.md) for the dated transition
record and [COMMERCIAL_USE_POLICY.md](COMMERCIAL_USE_POLICY.md) for the
commercial-use boundary.
