# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Private Graph mail observations on native startup/recovery/durable wake only.

Reuse the subscription transport and native ingest/provenance/atomic checkpoint
store. Nothing here schedules work, renews OAuth/subscriptions, sends mail or
accepts a document. A complete delta round and independent current message reads
are required before advancing any cursor. The selected folders remain explicit.
"""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit

# The native entrypoint also runs with -S and from outside the repository cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qikvrt_graph_subscription import Graph
from qikvrt_graph_webhook import BindingError, read_private, wire, EVENT_KEY
from qikvrt_api_handler import (
    HandlerConfig, run_handler, dirs, process_lock, atomic_write_bytes,
    _assert_safe_target, _strict_json_loads, _verify_ingest_provenance,
    MAX_PAYLOAD_BYTES,
)

SCOPE = "PRIVATE_GRAPH_MAIL_PROVIDER_OBSERVATION_ONLY"
ORIGIN = "https://graph.microsoft.com/v1.0/"
FIELDS = ("id", "parentFolderId", "changeKey", "lastModifiedDateTime",
          "receivedDateTime", "internetMessageId", "subject", "from",
          "hasAttachments", "isRead", "importance", "bodyPreview")
SELECT = "?$select=" + ",".join(FIELDS)
KEY = re.compile(r"mail-observation-[0-9a-f]{64}\Z")
FOLDER = re.compile(r"[A-Za-z0-9_=+\-]{1,256}\Z")
MAX_MESSAGES = 10000
MAX_PAGES = 128
MAX_READS = 12000


class ConsumerError(RuntimeError):
    """Incomplete/unbound provider state; no cursor or task acceptance."""


def digest(value):
    return hashlib.sha256(wire(value)).hexdigest()


def identifier(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 1024
            or any(ord(c) <= 32 or ord(c) >= 127 for c in value)):
        raise ConsumerError("bounded opaque provider identity required")
    return value


def delta_path(folder):
    return "/v1.0/me/mailFolders/" + quote(folder, safe="") + "/messages/delta"


def delta_url(url, folder):
    if not isinstance(url, str) or not 1 <= len(url) <= 16384:
        raise ConsumerError("bounded provider cursor required")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com"
            or parsed.fragment or parsed.path != delta_path(folder)
            or any(ord(c) <= 32 or ord(c) >= 127 for c in url)):
        raise ConsumerError("provider cursor differs from exact folder/origin")
    return url


def projection(remote, expected_id):
    if (not isinstance(remote, dict) or remote.get("id") != expected_id
            or not isinstance(remote.get("parentFolderId"), str)):
        raise ConsumerError("independent current message identity required")
    identifier(remote["parentFolderId"])
    result = {k: remote[k] for k in FIELDS if k in remote}
    if not {"lastModifiedDateTime", "receivedDateTime", "subject",
            "hasAttachments", "isRead", "bodyPreview"} <= set(result):
        raise ConsumerError("independent selected message content is incomplete")
    for k, value in result.items():
        if k in {"hasAttachments", "isRead"}:
            if not isinstance(value, bool):
                raise ConsumerError("provider message boolean required")
        elif k == "from":
            if value is not None:
                if not isinstance(value, dict) or set(value) != {"emailAddress"}:
                    raise ConsumerError("bounded sender projection required")
                address = value["emailAddress"]
                if (not isinstance(address, dict) or set(address) - {"name", "address"}
                        or any(not isinstance(v, str) or len(v) > 4096 for v in address.values())):
                    raise ConsumerError("bounded sender identity required")
        elif not isinstance(value, str) or len(value) > 8192:
            raise ConsumerError("bounded message field required")
    # A version marker or a usable selected content projection must be present.
    # Missing both is not an observable message, even if its ID is well formed.
    if not result.get("changeKey") and not all(k in result for k in (
            "lastModifiedDateTime", "subject", "receivedDateTime", "from",
            "hasAttachments", "isRead", "bodyPreview")):
        raise ConsumerError("message version or complete selected projection required")
    return result


def load_consumer_binding(path, webhook):
    value = _strict_json_loads(read_private(Path(path)))
    if not isinstance(value, dict) or set(value) != {
            "schema", "repository", "responsibility_owner", "state_root",
            "accepted_effect_scope", "tenant_id", "mailbox_id", "folder_ids", "token_file"}:
        raise BindingError("exact private mail consumer binding required")
    if (value["schema"] != "qikvrt_graph_mail_consumer_binding_v1"
            or value["accepted_effect_scope"] != SCOPE
            or any(value[k] != webhook[k] for k in (
                "repository", "responsibility_owner", "state_root"))
            or not webhook["subscriptions"]):
        raise BindingError("private consumer owner/repository/store/scope mismatch")
    identifier(value["mailbox_id"])
    if any(row["tenant_id"] != value["tenant_id"] or row["resource_prefix"] !=
           "users/" + value["mailbox_id"] + "/messages/" for row in webhook["subscriptions"]):
        raise BindingError("exact consumer tenant/mailbox binding required")
    folders = value["folder_ids"]
    if (not isinstance(folders, list) or not 1 <= len(folders) <= 32
            or any(not isinstance(f, str) or not FOLDER.fullmatch(f) for f in folders)
            or len(set(folders)) != len(folders)):
        raise BindingError("distinct bounded private folder scopes required")
    # The existing Graph transport reads the owner-only bearer itself.
    read_private(Path(value["token_file"]), limit=16384)
    return value


class GraphMailConsumer:
    def __init__(self, binding_path, *, api_factory=Graph):
        self.binding_path = binding_path
        self.api_factory = api_factory

    @staticmethod
    def _identity(binding):
        return {k: binding[k] for k in (
            "repository", "responsibility_owner", "state_root", "accepted_effect_scope",
            "tenant_id", "mailbox_id", "folder_ids")}

    @staticmethod
    def _cfg(binding, key, operation, payload=b""):
        return HandlerConfig(
            root=Path(binding["state_root"]), operation=operation, artifact_id=key,
            request_id=key if operation == "ingest" else "verify-" + key,
            payload_b64=base64.b64encode(payload).decode(), expected_sha256=key[-64:],
            dry_run=operation != "ingest", repository=binding["repository"],
            run_id="graph-mail-consumer", effect_accepted=True, origin_authenticated=True,
            responsibility_owner=binding["responsibility_owner"])

    def _packet(self, binding, key):
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise ConsumerError("private observation key required")
        locations = dirs(Path(binding["state_root"]))
        target = locations["inbox"] / (key + ".bin")
        raw = read_private(target, limit=MAX_PAYLOAD_BYTES)
        if hashlib.sha256(raw).hexdigest() != key[-64:]:
            raise ConsumerError("private observation digest mismatch")
        cfg = self._cfg(binding, key, "verify")
        provenance = _verify_ingest_provenance(
            cfg, artifact_id=key, payload_path=target,
            sidecar_path=locations["inbox"] / (key + ".bin.sha256"),
            metadata_path=locations["provenance"] / (key + "." + key + ".json"),
            payload=raw, sidecar_bytes=read_private(locations["inbox"] / (key + ".bin.sha256")))
        if provenance["responsibility_owner"] != binding["responsibility_owner"]:
            raise ConsumerError("private observation responsibility mismatch")
        packet = _strict_json_loads(raw)
        if (not isinstance(packet, dict) or set(packet) != {
                "schema", "binding", "previous_observation", "folders", "observation"}
                or packet["schema"] != "qikvrt_graph_mail_checkpoint_v1"
                or packet["binding"] != self._identity(binding)
                or set(packet["folders"]) != set(binding["folder_ids"])):
            raise ConsumerError("private checkpoint binding mismatch")
        prior_key = packet["previous_observation"]
        observation = packet["observation"]
        if (prior_key is not None and (not isinstance(prior_key, str) or not KEY.fullmatch(prior_key))
                or not isinstance(observation, dict)
                or observation.get("schema") != "qikvrt_graph_mail_observation_v1"
                or observation.get("effect_scope") != SCOPE
                or observation.get("provider_readback_performed") is not True
                or observation.get("native_mail_consumer_bound") is not True
                or observation.get("document_received") is not False
                or observation.get("effect_ack_done") is not False):
            raise ConsumerError("private observation boundary mismatch")
        for folder, state in packet["folders"].items():
            if not isinstance(state, dict) or set(state) != {"folder_id", "delta_link", "messages"}:
                raise ConsumerError("private folder state malformed")
            identifier(state["folder_id"])
            delta_url(state["delta_link"], folder)
            if not isinstance(state["messages"], dict) or len(state["messages"]) > MAX_MESSAGES:
                raise ConsumerError("private message state exceeds bound")
            for message_id, item in state["messages"].items():
                identifier(message_id)
                if (not isinstance(item, dict) or set(item) != {"sha256", "message"}
                        or projection(item["message"], message_id) != item["message"]
                        or item["message"]["parentFolderId"] != state["folder_id"]
                        or digest(item["message"]) != item["sha256"]):
                    raise ConsumerError("private message projection/hash mismatch")
        return packet

    def _load(self, binding):
        target = dirs(Path(binding["state_root"]))["out"] / "graph-mail-current.json"
        _assert_safe_target(target)
        if not target.exists():
            return target, None, None
        raw = read_private(target)
        pointer = _strict_json_loads(raw)
        if not isinstance(pointer, dict) or set(pointer) != {"schema", "observation_key"} or (
                pointer["schema"] != "qikvrt_graph_mail_current_v1"):
            raise ConsumerError("private current pointer malformed")
        return target, raw, self._packet(binding, pointer["observation_key"])

    def read_observations(self, webhook, *, after_key=None, limit=256):
        """Private inbox handoff: committed, provenance-verified rounds only.

        Ignore ingested candidates not reachable from the atomic checkpoint.
        The downstream inbox evaluator keeps its own accepted observation key;
        it must not infer document acceptance from these selected mail fields.
        """
        binding = load_consumer_binding(self.binding_path, webhook)
        if (not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10000
                or after_key is not None and (not isinstance(after_key, str) or not KEY.fullmatch(after_key))):
            raise ConsumerError("bounded private observation continuation required")
        with process_lock(Path(binding["state_root"])):
            _, raw, packet = self._load(binding)
            key = _strict_json_loads(raw)["observation_key"] if raw else None
            rows, seen = [], set()
            while key is not None and key != after_key:
                if key in seen or len(rows) >= limit:
                    raise ConsumerError("private observation continuation exceeds bound or cycles")
                seen.add(key)
                packet = self._packet(binding, key)
                rows.append({"observation_key": key, "observation": packet["observation"]})
                key = packet["previous_observation"]
            if key != after_key:
                raise ConsumerError("private inbox continuation anchor is not committed")
        return list(reversed(rows))

    def observe(self, webhook, *, event_keys=(), lifecycle=(), trigger="START_RECOVERY_OR_WAKE",
                binding_guard=None):
        binding = load_consumer_binding(self.binding_path, webhook)
        root = Path(binding["state_root"])
        if any(not isinstance(k, str) or not EVENT_KEY.fullmatch(k) for k in event_keys):
            raise ConsumerError("verified native ingress keys required")
        with process_lock(root):
            target, before, previous = self._load(binding)
        api = self.api_factory(binding["token_file"])
        reads = []

        def read(url, *, account=False):
            if len(reads) >= MAX_READS:
                raise ConsumerError("provider read round exceeds bound")
            value = api.request("GET", "me?$select=id") if account else api.mail_get(url)
            if not isinstance(value, dict):
                raise ConsumerError("provider JSON object required")
            trace = getattr(api, "last_readback", None)
            reads.append({"url": url, "canonical_json_sha256": digest(value),
                          "raw_readback": trace if isinstance(trace, dict) else None})
            return value

        account = read(ORIGIN + "me?$select=id", account=True)
        if account.get("id") != binding["mailbox_id"]:
            raise ConsumerError("authenticated Graph mailbox differs from binding")
        folders, changes, resolved = {}, [], set()
        resynced = []
        for folder in binding["folder_ids"]:
            remote_folder = read(ORIGIN + "me/mailFolders/" + quote(folder, safe="") + "?$select=id")
            folder_id = identifier(remote_folder.get("id"))
            if folder_id in resolved:
                raise ConsumerError("folder aliases resolve to the same provider scope")
            resolved.add(folder_id)
            prior = previous["folders"][folder] if previous else None
            if prior and prior["folder_id"] != folder_id:
                raise ConsumerError("provider folder identity changed; explicit recovery required")
            initial = "https://graph.microsoft.com" + delta_path(folder) + SELECT

            def round_pages(start):
                url, seen, touched = delta_url(start, folder), set(), set()
                for _ in range(MAX_PAGES):
                    if url in seen:
                        raise ConsumerError("cyclic provider pagination")
                    seen.add(url)
                    page = read(url)
                    rows = page.get("value")
                    links = [k for k in ("@odata.nextLink", "@odata.deltaLink") if k in page]
                    if not isinstance(rows, list) or len(rows) > MAX_MESSAGES or len(links) != 1:
                        raise ConsumerError("complete bounded delta page required")
                    for row in rows:
                        if not isinstance(row, dict):
                            raise ConsumerError("delta message identity required")
                        touched.add(identifier(row.get("id")))
                    if len(touched) > MAX_MESSAGES:
                        raise ConsumerError("delta message collection exceeds bound")
                    url = delta_url(page[links[0]], folder)
                    if links[0] == "@odata.deltaLink":
                        return touched, url
                raise ConsumerError("delta pagination exceeds bound")

            full = prior is None
            try:
                touched, cursor = round_pages(prior["delta_link"] if prior else initial)
            except HTTPError as exc:
                # A provider-declared expired cursor permits one bounded reset
                # in this same event. Partial pages/cursors are never committed.
                if exc.code != 410 or prior is None:
                    raise
                full = True
                resynced.append(folder)
                touched, cursor = round_pages(initial)
            old = prior["messages"] if prior else {}
            current = {} if full else copy.deepcopy(old)
            for message_id in sorted(touched):
                try:
                    remote = read(ORIGIN + "me/messages/" + quote(message_id, safe="") + SELECT)
                except HTTPError as exc:
                    if exc.code != 404:
                        raise
                    remote = None
                    reads.append({"url": ORIGIN + "me/messages/" + quote(message_id, safe=""),
                                  "status": 404})
                if remote is None:
                    current.pop(message_id, None)
                else:
                    item = projection(remote, message_id)
                    if item["parentFolderId"] == folder_id:
                        current[message_id] = {"sha256": digest(item), "message": item}
                    else:
                        current.pop(message_id, None)  # moved out of this explicit folder
            for message_id in sorted(set(old) | set(current)):
                if old.get(message_id) == current.get(message_id):
                    continue
                item = current.get(message_id)
                changes.append({"folder": folder, "message_id": message_id,
                                "kind": "UPSERT" if item else "REMOVED_FROM_FOLDER",
                                "previous_sha256": old.get(message_id, {}).get("sha256"),
                                "sha256": item["sha256"] if item else None,
                                "message": item["message"] if item else None})
            folders[folder] = {"folder_id": folder_id, "delta_link": cursor, "messages": current}
        if sum(len(f["messages"]) for f in folders.values()) > MAX_MESSAGES:
            raise ConsumerError("selected message state exceeds bound")
        source = getattr(api, "source", "SYNTHETIC_TEST_PROVIDER")
        observation = {
            "schema": "qikvrt_graph_mail_observation_v1", "effect_scope": SCOPE,
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider_source": source, "trigger": trigger,
            "coverage": "CONFIGURED_FOLDERS_SELECTED_MESSAGE_FIELDS",
            "tenant_binding_basis": "PRIVATE_CONFIGURATION_NOT_TOKEN_ATTESTATION",
            "provider_readbacks": reads, "resynced_folders": resynced,
            "ingress_event_keys": sorted(set(event_keys)),
            "lifecycle_signals": sorted(set(lifecycle)), "changes": changes,
            "native_mail_consumer_bound": True, "provider_readback_performed": True,
            "document_received": False, "effect_ack_done": False,
        }
        packet = {"schema": "qikvrt_graph_mail_checkpoint_v1", "binding": self._identity(binding),
                  "previous_observation": _strict_json_loads(before)["observation_key"] if before else None,
                  "folders": folders, "observation": observation}
        encoded = wire(packet)
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise ConsumerError("private checkpoint exceeds native storage bound")
        key = "mail-observation-" + hashlib.sha256(encoded).hexdigest()
        result = run_handler(self._cfg(binding, key, "ingest", encoded))
        if (result.get("effect_state") != "EFFECT_ACK_DONE"
                or result.get("effect_scope") != "opaque-byte-storage-only"
                or result.get("sha256") != key[-64:]):
            raise ConsumerError("private provider observation not durably stored")
        with process_lock(root):
            # Network reads occur outside the shared native lock. A concurrent
            # writer/binding change cannot be silently lost at checkpoint commit.
            if load_consumer_binding(self.binding_path, webhook) != binding:
                raise BindingError("private consumer binding changed during provider read")
            if binding_guard is not None and binding_guard() != webhook:
                raise BindingError("private ingress binding changed during provider read")
            _, actual, _ = self._load(binding)
            if actual != before:
                raise ConsumerError("private provider cursor changed concurrently")
            if self._packet(binding, key) != packet:
                raise ConsumerError("independent provider observation readback mismatch")
            pointer = wire({"schema": "qikvrt_graph_mail_current_v1", "observation_key": key})
            atomic_write_bytes(target, pointer)
            if read_private(target) != pointer:
                raise ConsumerError("independent provider cursor readback mismatch")
        # Health is public: no account/folder/message identities, cursor, sender,
        # subject, opaque Graph error, token or private observation key escapes.
        return {"status": "OBSERVED", "effect_scope": SCOPE, "changes": len(changes),
                "native_mail_consumer_bound": True, "provider_readback_performed": True,
                "document_received": False, "effect_ack_done": False}
