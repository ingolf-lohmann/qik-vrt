<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Original-host REST adapter: systemd user-service IaC candidate

This is an **opt-in, original-user-host** unit template for the existing
`production-environment` REST implementation. It neither creates credentials,
registers an IdP, changes DNS, deploys containers nor establishes runtime admission.
It is not a substitute for the native Terminal/Transputer or EAP.

**Identity binding:** use only the admitted original Linux user whose SSO profile,
OS Secret Service session and private material are already registered. It must
run through that user's `systemd --user` manager (not a new system user).
Confirm that this manager actually has access to the original D-Bus/Secret
Service session and registered OIDC origin. User lingering alone is not evidence
of an accessible Secret Service or of admission.

Render `qikvrt-original-adapter.service.in` using independently verified
**non-secret host facts**: exact sealed package root, Python executable with
original pinned SSO dependencies, and absolute path to the original protected
environment file. Do not derive these from untrusted PR inputs. Never put the
private environment file, credentials or browser state into Git.

The protected environment must retain the existing expiring API credential,
repository and principal, `QIKVRT_SSO_STATE_DIR`,
`QIKVRT_SSO_AUTH_CONFIG`, optional SSO profile and optionally BOTH
`QIKVRT_PRODUCTION_MATERIAL_SOURCE` and
`QIKVRT_PRODUCTION_MATERIAL_SOURCE_SHA256`. Original OS Secret Service,
profile writer lock, and independently approved host-material files must
remain available to that user. The adapter validates authorization/material
before provider writes. Binding is fixed to `127.0.0.1`; NEVER open port 8766.

After independent original-host identity/admission and unit render review,
execute **as that original user, with the original session**:

```sh
mkdir -p "$HOME/.config/systemd/user"
install -m 0644 rendered-qikvrt-original-adapter.service \
  "$HOME/.config/systemd/user/qikvrt-original-adapter.service"
systemctl --user daemon-reload
systemctl --user enable --now qikvrt-original-adapter.service
systemctl --user is-active qikvrt-original-adapter.service
```

Use the existing authenticated local `/personal/` SSO login and original
`productionEnvironmentReadback` GET at the same registered loopback origin.
Only after exact Main/source/material admission may the existing REST handoff
write the five scoped protected GitHub `qikvrt-production` bindings. Proceed
with the existing mTLS `container-host-identity` GET `/v1.45/info`, protected
container deploy, HTTPS/runtime and native EAP readbacks. All remain
independent acceptance gates.

**Fail closed:** absent host identity, inaccessible original SSO/Secret Service,
unavailable private material, unclean source, wrong loopback origin or failed
startup leaves production unchanged. Unit activation is NOT `EFFECT_ACK_DONE`.
