# QIK-VRT Threat Model Summary

Primary risks:

- leaked tokens
- unauthorized workflow mutation
- stale node heartbeat
- false PASS claims from stale evidence
- unauthorized expansion beyond known nodes

Controls:

- hidden local token prompt
- no embedded token
- run-id scoped evidence waits
- known-node registry only
- no global scanning
- seed and node self-write boundaries


## Safety/Security deployment assurance — Owner authorization, 19 October 2026

QIKVRT and the Effect Acknowledgement Protocol are intended for Safety and
Security applications as well. The requirements and source/applicability
register is [QIKVRT_SAFETY_SECURITY_IMPACT_20261019_V1](../state/work_units/QIKVRT_SAFETY_SECURITY_IMPACT_20261019_V1.json).
These are engineering requirements with open deployment acceptance, not
certification, legal conformity or a verified physical installation.

The existing five-state protocol and DONE-only ordinary-release rule remain
the effect boundary. A received command, a transport ACK and a physical
condition are separate claims. A physical adapter must bind the exact actuator,
authorized transition, configuration and fresh observation evidence; it cannot
claim a door is secured merely because a command or relay output was accepted.

| Threat or dependency | Required assurance and acceptance |
| --- | --- |
| Cloud, identity, licensing or supplier outage | Declare an isolation interval; test local decisions, revocation/freshness rules, emergency access and vendor-independent recovery. |
| Egress or alarm blocked by a remote gate | Bind a site-specific hazard analysis; retain separately admitted local safety paths and test fire, power loss and network loss together. No universal fail-open/fail-closed assumption. |
| Forged, stale or conflicting physical feedback | Bind source, effect ID, policy and observation window; test replay, sensor conflict, stuck actuators and ambiguous responses. |
| Reader bus or credential compromise | Test authenticated links, commissioning, key lifecycle and exact controller/reader/credential/firmware interoperability. |
| Compromised or unsupported firmware | Require authenticated update provenance and compatibility; test isolated interrupted-update recovery and a verified forward-repair path. |
| Partition, crash, takeover or full audit store | Reuse native durable journals/fencing; declare RTO and storage limits; prove the claimed workload's acknowledgement/replay and local audit behavior. |
| Supplier assurance or legal scope overstated | Separate primary evidence, manufacturer claims and engineering derivation; retain exact scope, applicability and open evidence duties. |

ASD's OT guidance is a useful assurance input, not EU legislation. Its
publication does not establish QIKVRT compliance. The Gallagher T30 announcement
is an unverified manufacturer approval claim and supplies a procurement
evidence request, not a new QIKVRT dependency. IEC/SIA product/profile evidence
does not establish the interoperability or safety of a whole installation.
For EU CRA reporting, first determine the actual product and operator role;
record the applicable awareness-based deadlines and responsible route without
automatically sending a live notification.

Every new material source change follows the register's change-intake process.
Preserve older source identities and open tests; only bound acceptance evidence
can close the corresponding deployment obligation. No additional executor,
client timer or implicit IETF/Zenodo publication is introduced.

### SS-03 reproducible simulation controls

Run the existing native gate with `make conformance`, or only the new cases:

```sh
python3 -B -m unittest -v tests.test_physical_effect_ack_conformance.PhysicalEffectSimulationConformanceTests
```

The original 41-case module remains byte-frozen because it is a published
source-bound original. The 22 additional cases in that class use the original `effect_ack_sync`, protocol hash
and chain validators, native TEMDD Ledger, and the Terminal's fresh read-only
readback. No production adapter, protocol field, state, service or executor is
added. `_PhysicalEffectSimulation` is a test-only evidence oracle. Its supported
transition is explicitly `unsecured` to `secured`; fixture milliseconds, grants,
observer identities and independence are assumptions, not hardware measurements
or authenticated device identities. The raw command binds effect ID, actuator,
requested transition, principal, authorization, policy, configuration and
firmware. Separate contact and bolt observations bind that command hash, source,
sequence and capture time. Evidence references hash the exact canonical bytes.

| Control | Expected model result |
| --- | --- |
| Matching independent simulated feedback | DONE for this simulation only |
| Command accepted or output changed, physical readback missing | CONTINUE |
| Lost command reply | CONTINUE until fresh independent readback; one dispatch only |
| No checkable information reception | NACK |
| Unresponsive actuator | CONTINUE before, BLOCK after the declared observation deadline |
| Stuck actuator despite output/command ACK | BLOCK |
| Contradictory, unknown, duplicate or actuator-supplied observer | ISOLATE; retain both signals |
| Mismatched actuator, transition, effect, grant, policy, configuration, firmware or command hash | BLOCK |
| Denied, revoked or expired grant | BLOCK even with matching sensors |
| Observation older than 100 fixture ms, captured before command, or in the future | BLOCK; delivery time cannot refresh capture time |
| Unbounded/uncertain observation clock, or missing required sensor | CONTINUE |
| Old or consumed per-observer sequence; another effect's DONE | BLOCK |
| Identical current readback of the same effect | Idempotent protocol; no second actuation |
| Previously accepted observation becomes stale | New protective BLOCK version; retain original DONE bytes |
| Changed input with the same effect identity | Core predecessor-integrity BLOCK; no inherited DONE |
| Unsupported transition | BLOCK rather than borrowing the secured-state interpretation |

These dispositions are explicit simulation policy, not universally prescribed
site hazard responses. Local emergency/egress action remains the separately
admitted SS-02 path; the suite never operates it. A deliberate bad-adapter
control demonstrates that unchecked Boolean assertions can still make the pure
core return DONE. Passing this suite therefore proves the model controls and
core mapping only; it does not install a physical validator or establish
physical-adapter conformance. The native test persists both original simulated
sensor signals and the protocol, independently reads them, checks digests and
deduplication, and keeps hardware acceptance and global DONE false.

`SS-03 = OPEN_PHYSICAL_ADAPTER_CONFORMANCE` remains unchanged in the original
requirements register. To close a deployment-specific obligation, bind an
admitted actual adapter, actuator and independent measurement channels; declare
authorization/trust roots, exact policy/configuration/firmware, capture-clock
uncertainty, freshness/settling bounds and replay-state persistence. Repeat the
positive and fault cases on that hardware, retain original device and sensor
traces, demonstrate recovery without duplicate ambiguous actuation, and obtain
fresh independent Terminal readback for the exact installation. Simulation,
real hardware testing, hazard assessment and safety/security certification
remain separate evidence classes. No certification is claimed by these tests.
