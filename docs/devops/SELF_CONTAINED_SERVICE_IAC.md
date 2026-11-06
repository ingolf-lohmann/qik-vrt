<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# QIK-VRT: self-contained Infrastructure as Code in every service instance

Owner decision: 2026-11-06. Every instance offering a QIK-VRT service MUST carry its own **version-pinned, independently verifiable infrastructure definition** in its sealed package, not merely a link to a central GitHub repository.

Every such package MUST include its runtime, universal Terminal and Transputer, EAP gate, supervision and recovery specifications, service and host adapters, immutable source identity, dependency closures, non-secret environment schema, health probes, rollback rules, bounded fault handling and independently retained audit/readback contracts. The package must be sufficient to reproduce the instance on an admitted compatible host without fetching mutable development artifacts.

Deployment is not necessarily independent of provider APIs, externally administered DNS/TLS, protected secrets, durable disks or a privileged executor. These remain declared external *dependencies* and admission gates. A sealed bundle must NOT embed credentials, private keys, provider sessions or an unverified claim that an instance is online.

The candidate policy is `policy/QIKVRT_SELF_CONTAINED_SERVICE_IAC_V1.json`. The static gate is `tools/qikvrt_instance_iac.py`, invoked against a JSON instance descriptor:

```sh
python3 -B tools/qikvrt_instance_iac.py --root <verified-package-root> --instance <instance-descriptor.json>
```

Minimum descriptor: `instance_id`, `service_id`, exact `source_head` and `source_tree` (40 lowercase hex), `package_digest_sha256`, `deployment_adapter`, `runtime_roles`, `healthcheck`, `rollback`, `secret_refs`, `evidence_sink`. Protected inputs use **references**, not contents (for example `env://QIKVRT_HOST_BINDING`), and must be independently bound at the admitted original host.

**Admission is two stage:** (1) static package compliance, CI regression, deterministic integrity regeneration and signed/source-bound package readback; (2) protected real host deployment, native Terminal/Transputer tests, fault cases and original independent effect readback. Stage 1 never implies stage 2. Missing provider-native credentials or runtime gates fail closed.

This candidate is a *contract and static checker*, not yet an enforcement hook in the S1 pack/verify pipeline. It must be integrated after regression and reviewed for complete service inventory; an absent instance is not proven compliant. No permission to merge, publish, change DNS, or assert `EFFECT_ACK_DONE` follows from this document.
