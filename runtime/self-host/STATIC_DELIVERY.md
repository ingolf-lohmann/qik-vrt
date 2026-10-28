# Minimal static delivery through the existing S1 adapter

The Owner's 2026-10-28 instruction is to correct raumzeitterminal.de and
deliver a minimal Hello World through the existing IONOS VPS. Preparing HTML
alone does not satisfy that instruction. These operations extend
tools/qikvrt_self_host.py and its existing provider adapter and private
receipt store. They create no server, replacement runtime, scheduler or account.

## Existing-host connection

Use a protected JSON file, mode 0600, with schema
qikvrt-owned-host-static-binding/v1 and these fields:

    {
      "schema": "qikvrt-owned-host-static-binding/v1",
      "provider": "ionos",
      "product": "vps",
      "contract_id": "<actual existing contract identifier>",
      "server_id": "<actual existing VPS identifier>",
      "host": "<independently verified public VPS IP>",
      "port": 22,
      "user": "<existing SSH user>",
      "domain": "raumzeitterminal.de",
      "webroot": "<existing inspected webserver document root>",
      "identity_file": "<existing protected absolute key-file reference>",
      "known_hosts_file": "<existing protected absolute known-hosts reference>",
      "known_hosts_sha256": "<independently obtained SHA-256 of that public host-key file>",
      "authorization_reference": "<retained actual Owner production authorization>"
    }

Placeholders are deliberately invalid. Test addresses, a contract number,
readable DNS, and a provider readiness email are not a host binding.
Private keys are never generated, printed, placed in Git or placed in receipts.
The SSH client uses strict host-key checking, one connection attempt, no
password/keyboard-interactive fallback, no agent forwarding, and no proxy or
connection-sharing configuration. The Linux target requires /usr/bin/python3
with the standard-library filesystem operations used by the original adapter.
No package or webserver is implicitly installed.

## File effect before DNS effect

Run the existing S1 entrypoint:

    python3 -B tools/qikvrt_self_host.py host-static-readback \
      --production-binding /private/existing-host.json \
      --binding-sha256 ACTUAL_BINDING_SHA256

    python3 -B tools/qikvrt_self_host.py host-static-upload \
      --production-binding /private/existing-host.json \
      --binding-sha256 ACTUAL_BINDING_SHA256 \
      --static-file runtime/self-host/hello-world/index.html \
      --static-file-sha256 ACTUAL_FROZEN_PAGE_SHA256 \
      --expected-static-sha256 ACTUAL_OLD_INDEX_SHA256_OR_ABSENT \
      --host-operation-id OWNER_BOUND_OPERATION_ID \
      --provider-receipts /private/existing-receipts

The last expected value is exactly ABSENT only after an independent read
shows no index. The adapter preserves the previous bytes privately, writes a
create-only intent, transfers the exact bounded page, replaces index.html
within the same directory, fsyncs, and performs a separate SSH readback.
Cooperating S1 writers share a lock. An existing page requires the bound old
digest; an absent page uses an atomic no-overwrite link. This is not a general
filesystem CAS against unrelated privileged writers.

An uncertain upload is never replayed. Use host-static-reconcile with the
same binding, operation ID and private receipt directory. File verification
does not claim HTTPS delivery, native runtime acceptance or EFFECT_ACK_DONE.
The static page itself requires no running Mesh or Firefox.

## Routing cutover through the documented IONOS DNS API

tools/qikvrt_ionos_dns.py web-readback --zone raumzeitterminal.de reads the
whole existing zone, including apex, www, mail and redirect-related TXT records.
Use its web_records_sha256 with web-apply --target-ipv4 ACTUAL_VPS_IPV4
--expected-records-sha256 ACTUAL_WHOLE_ZONE_SHA256. Only existing apex/www
routes are changed. A www CNAME can be bound to the apex; an existing www A
can be changed to the same original VPS. IPv6 disabling requires the separate
explicit --disable-web-aaaa flag. No zone, server or record is created or
deleted. Reobserve the full zone before and after each PUT.

IONOS documents that DNS updates can deactivate conflicting service records.
An unexpected service side effect is retained as a partial result and stops
later writes. The adapter does not assert that an unobserved hosting control
setting was removed. The acceptance criterion is fresh exact page delivery
at the requested domain, with the old redirect absent.

Run host-static-public-readback --static-file-sha256 ACTUAL_PAGE_SHA256
after actual routing/TLS configuration. Both apex and www HTTPS responses
must be 200, use their exact URLs without redirects, and match the frozen
page bytes. Missing TLS, inaccessible readback or another page remains HOLD.

## Primary provider documentation

- IONOS DNS API, version 1.0.2:
  https://developer.hosting.ionos.de/docs/dns
- Original OpenAPI specification, including existing-record PUT and the
  conflicting-service warning:
  https://developer.hosting.ionos.de/assets/kms-swagger-specs/dns.yaml
- IONOS: Cloud Server first steps, SSH access, SFTP and static-IP domain mapping:
  https://www.ionos.de/hilfe/server-cloud-infrastructure/erste-schritte/cloud-server-erste-schritte/
- IONOS: File upload via SFTP:
  https://www.ionos.de/hilfe/hosting/ftp-zugaenge-einrichten-und-verwalten/dateien-per-sftp-mit-filezilla-uebertragen/

These documents establish provider-supported mechanisms. They do not supply
this session's protected connection, prove VPS identity, or prove deployment.
