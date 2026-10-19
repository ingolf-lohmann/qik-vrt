<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# Explicit TEMDD carrier binding

The ledger's `serve` command requires an explicitly supplied `--repository`
and positive `--pr`. It no longer substitutes the historical reference values
`Goldkelch/qik-vrt` and `1103`. A missing or invalid binding returns `HOLD`
before creating the state directory, ledger, or listeners. `append` keeps its
existing interface: the submitted original event carries its subject, and the
running carrier validates it.

The container entrypoint requires `QIKVRT_TEMDD_REPOSITORY` and
`QIKVRT_TEMDD_PR` for every launch, including an unsealed reference launch.
Both are validated before runtime side effects and passed as separate arguments.
Existing launchers that already supply both values retain their binding.

Use the actual carrier repository and its established PR association. The
last merged PR, a publication cited by an input, or an arbitrary placeholder
does not become the carrier's PR merely because its number is available.
The current subject schema still requires a positive PR; this change does not
introduce or claim a PR-independent node-subject schema. Explicit arguments
prevent accidental defaults; they do not authenticate a claimed PR association.

If a predecessor ran with the wrong subject, preserve its original event bytes,
IDs, epoch, digests and receipts as historical evidence. Do not relabel them or
reset its journal to manufacture a successful join. A corrected carrier is a
successor with fresh evidence obligations. The existing ledger partitions replay
by exact subject; the regression verifies that the old stored row is preserved
and is not replayed under the corrected subject.

Local append/readback proves only that bounded local persistence effect. It
does not prove Seed acceptance, authenticated native-effect replication, writer
fencing, a durable host, or delivery on `raumzeitterminal.de`. A lifecycle branch
and queue row must use the existing node registration and Seed contracts.

Tests extend `tests/test_temdd_event_ledger.py` and
`tests/test_temdd_runtime_subject_binding.py`. They reject omitted direct-CLI
bindings before state creation, exercise an explicitly bound real CLI process,
check predecessor-byte preservation, and execute the actual shell admission
guard. A fixture's PR number is synthetic test data, not a production binding.
