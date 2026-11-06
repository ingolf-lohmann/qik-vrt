<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Original-host REST adapter: systemd IaC candidate

This is an **opt-in, on-original-host** unit template for the existing
`production-environment` REST implementation. It neither creates credentials,
registers an IdP, changes DNS, deploys containers nor establishes runtime admission.
It is not a substitute for native Terminal/Transputer or EAP.

Render `qikvrt-original-adapter.service.in` with independently verified
**non-secret host facts**: dedicated service user/group, exact sealed package root,
Python executable with original pinned SSO dependencies, absolute protected
environment-file location. Do not derive these values from untrusted PR inputs.
Never put the private environment file into Git.

The private on-host environment must retain the existing, admitted expiring API
credential, principal, repository, `QIKVRT_SSO_STATE_DIR`,
`QIKVRT_SSO_AUTH_CONFIG`, optional SSO profile, and optionally **both**
`QIKVRT_PRODUCTION_MATERIAL_SOURCE` and
`QIKVRT_PRODUCTION_MATERIAL_SOURCE_SHA256`. Existing OS Secret Service,
original profile writer lock and independently approved host-material files
must remain accessible to the service principal. The original adapter validates
authorization and material before provider writes. Binding stays on
`127.0.0.1`; never publish the loopback REST service to the Internet.

After host identity and render validation, on the **original** admitted host:

```sh
sudo install -m 0644 rendered-qikvrt-original-adapter.service /etc/systemd/system/qikvrt-original-adapter.service
sudo systemctl daemon-reload
sudo systemctl enable --now qikvrt-original-adapter.service
sudo systemctl is-active qikvrt-original-adapter.service
```

Perform the original authenticated local `/personal/` SSO login and
`productionEnvironmentReadback` GET. Only after exact Main/source/material
admission may the existing REST handoff write the five scoped protected GitHub
`qikvrt-production` inputs. Continue with the existing mTLS
`container-host-identity` GET `/v1.45/info`, protected container-deploy,
HTTPS and native EAP readbacks. All these are independent gates.

**Fail closed:** no host identity, missing original SSO/Secret Service,
unavailable original protected material, unclean source or failed startup
leaves production unchanged. Unit activation is not `EFFECT_ACK_DONE`.
