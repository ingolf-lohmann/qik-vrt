<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# License transition record

**Transition date:** 2026-07-20

**Rights holder stated by the repository:** Ingolf Lohmann

## Current licensing decision

For distributions of the current QIK-VRT repair set and later QIK-VRT-owned
software that carry the new notice, the public source-code license is
`PolyForm-Noncommercial-1.0.0`. The standard license permits use, change, and
distribution for its permitted noncommercial purposes. Commercial use is not
granted and requires a separate written agreement from the rights holder.

This is a source-available, noncommercial license. It is not represented as an
OSI-approved open-source license.

## No retroactive withdrawal

The public baseline at commit
`8ae1884116221087bdcc75eed9905bb80bdd9e95`, earlier releases, and any file
validly received under Apache-2.0 remain usable under the Apache-2.0 grant
attached to that version or file. Those already granted perpetual and
irrevocable rights are not withdrawn by this transition. The retained text at
`LICENSES/Apache-2.0.txt` exists for that historical and third-party boundary;
it is not the default license for newly licensed QIK-VRT code.

## Rights-chain boundary

This transition applies only to material for which Ingolf Lohmann holds the
rights required to grant the new license. Third-party software, dependencies,
standards material, and contributions not owned or relicensable by him retain
their own licenses. A file-level SPDX identifier or specific third-party
notice overrides the repository default.

The repository contains helper paths that can download a separately licensed
Python runtime, but it does not thereby relicense Python. If a Python runtime
or another third-party binary is distributed with QIK-VRT in the future, that
distribution must also carry the complete license text and notices required by
the exact third-party version being shipped.

At the transition review, the shallow baseline exposed only a grafted
GitHub-Actions commit and could not by itself prove the complete authorship
chain. A later publication commit does not repair missing historical rights
evidence. Before a
public release of the relicensed whole, the owner should retain evidence of
authorship, assignments, contributor permissions, or a clean-room replacement
for any contribution not solely owned by him.

## Future contributions

No contribution should be merged merely on the assumption that an Apache-era
contribution rule remains sufficient. Future contributions require written
terms that authorize both the noncommercial public license and any separate
commercial licensing by the project rights holder. See CONTRIBUTING.md.
