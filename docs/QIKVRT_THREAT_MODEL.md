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
