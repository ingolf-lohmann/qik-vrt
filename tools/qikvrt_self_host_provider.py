#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Provider admission extension of S1, not a second launcher or host supervisor.

Inventory is GET-only. A create is a separate exact-request-authorized effect.
Private immutable receipts fence cooperating executors before the first POST;
an uncertain outcome permits reconciliation, never another POST. No delete,
terms acceptance, key generation, credential discovery or deployment exists here.
"""
from __future__ import annotations

import base64
import contextlib
import datetime as dt
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import urllib.error
import urllib.parse
import urllib.request

try:
    from . import qikvrt_self_host as host
    from .qikvrt_subprocess import run_bounded
except ImportError:
    import qikvrt_self_host as host
    from qikvrt_subprocess import run_bounded

PRODUCTS = {"digitalocean": ("digitalocean-v2", "https://api.digitalocean.com/v2"),
            "ionos": ("ionos-cloud-v6", "https://api.ionos.com/cloudapi/v6"),
            "hetzner": ("hetzner-cloud-v1", "https://api.hetzner.cloud/v1")}
SNAPSHOT = "qikvrt-provider-inventory/v1"
REQUEST = "qikvrt-provider-admission-request/v1"
MAX_RESPONSE = 8 * 1024 * 1024
MAX_PAGES = 100
MAX_AGE = 300
TOKEN_ENV = {"digitalocean": "DIGITALOCEAN_TOKEN", "ionos": "IONOS_TOKEN", "hetzner": "HCLOUD_TOKEN"}


def wire(value):
    return host.raw_json(value)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def decode(data):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError("DUPLICATE_PROVIDER_JSON_KEY")
            value[key] = item
        return value
    def finite(_): raise ValueError("NONFINITE_PROVIDER_JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=finite)


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def instant(value):
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() is None: raise ValueError()
        return result
    except (AttributeError, TypeError, ValueError):
        raise ValueError("PROVIDER_UTC_TIME_REQUIRED") from None


def fresh(value, now=None):
    age = ((now or dt.datetime.now(dt.timezone.utc)) - instant(value)).total_seconds()
    if not -5 <= age <= MAX_AGE: raise ValueError("HOLD_PROVIDER_OBSERVATION_NOT_FRESH")


def pin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) or value == "0" * 64:
        raise ValueError("INDEPENDENT_NONZERO_PROVIDER_PIN_REQUIRED")
    return value


def pinned(path, expected):
    if not isinstance(path, Path): raise ValueError("EXACT_PRIVATE_PROVIDER_INPUT_REQUIRED")
    host.private_path(path)
    if path.stat().st_size > MAX_RESPONSE or path.stat().st_nlink != 1:
        raise ValueError("BOUNDED_SINGLE_LINK_PROVIDER_FILE_REQUIRED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        data = source.read(MAX_RESPONSE + 1)
    if sha(data) != pin(expected): raise ValueError("PROVIDER_INPUT_PIN_MISMATCH")
    return decode(data)


def identifier(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", str(value)):
        raise ValueError("EXACT_PROVIDER_RESOURCE_ID_REQUIRED")
    return str(value)


def catalog_id(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,120}", str(value)) or ".." in str(value):
        raise ValueError("EXACT_PROVIDER_CATALOG_ID_REQUIRED")
    return str(value)


def public_key(value):
    """Bind actual SSH wire bytes; comments and display fingerprints are not identity."""
    if not isinstance(value, str) or len(value) > 16384 or any(c in value for c in "\r\n\0"):
        raise ValueError("PUBLIC_SSH_KEY_REQUIRED")
    parts = value.split()
    if len(parts) < 2 or parts[0] not in {"ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"}:
        raise ValueError("PUBLIC_SSH_KEY_REQUIRED")
    try: blob = base64.b64decode(parts[1], validate=True)
    except ValueError: raise ValueError("PUBLIC_SSH_KEY_REQUIRED") from None
    length = int.from_bytes(blob[:4], "big")
    if not 32 <= len(blob) <= 12288 or blob[4:4 + length] != parts[0].encode():
        raise ValueError("PUBLIC_SSH_KEY_WIRE_TYPE_MISMATCH")
    return {"public_key": parts[0] + " " + parts[1], "sha256": sha(blob)}


def money(value):
    try: number = Decimal(str(value))
    except (InvalidOperation, ValueError): raise ValueError("FINITE_PROVIDER_PRICE_REQUIRED") from None
    if not number.is_finite() or number < 0 or number > Decimal("1000000"):
        raise ValueError("FINITE_PROVIDER_PRICE_REQUIRED")
    return number


def origin(value):
    if not isinstance(value, str): raise ValueError("PUBLIC_HTTPS_ORIGIN_REQUIRED")
    parsed = urllib.parse.urlsplit(value)
    name = parsed.hostname or ""
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.path
            or parsed.query or parsed.fragment or parsed.port not in {None, 443}
            or len(name) > 253 or not re.fullmatch(r"(?:" + label + r"\.)+" + label, name)
            or name.endswith((".localhost", ".local", ".invalid", ".test"))):
        raise ValueError("PUBLIC_HTTPS_ORIGIN_REQUIRED")
    try:
        if not ipaddress.ip_address(name).is_global: raise ValueError("PUBLIC_HTTPS_ORIGIN_REQUIRED")
    except ValueError:
        if re.fullmatch(r"[0-9.]+", name): raise ValueError("PUBLIC_HTTPS_ORIGIN_REQUIRED")
    return name


def ipv4(value):
    try: address = ipaddress.ip_address(value)
    except (ValueError, TypeError): raise ValueError("HOLD_PUBLIC_IPV4_UNAVAILABLE") from None
    if address.version != 4 or not address.is_global: raise ValueError("HOLD_PUBLIC_IPV4_UNAVAILABLE")
    return str(address)


class ProviderError(ValueError):
    def __init__(self, status, cause):
        self.status, self.cause = status, cause
        super().__init__(cause)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError(code, "HOLD_PROVIDER_REDIRECT_FORBIDDEN")


class API:
    """Fixed provider origins, no proxy/redirect, bounded requests, no automatic retry."""
    def __init__(self, provider, token, binding, opener=None):
        if provider not in PRODUCTS: raise ValueError("SUPPORTED_PROVIDER_REQUIRED")
        product, self.base = PRODUCTS[provider]
        if (not isinstance(binding, dict) or binding.get("product") != product
                or not isinstance(binding.get("principal_id"), str) or not binding["principal_id"].strip()):
            raise ValueError("HOLD_EXACT_PROVIDER_PRODUCT_AND_PRINCIPAL_BINDING_REQUIRED")
        pin(binding.get("principal_evidence_sha256"))
        if not isinstance(token, str) or not 16 <= len(token) <= 4096 or any(c.isspace() for c in token):
            raise ValueError("HOLD_PROVIDER_CREDENTIAL_UNBOUND")
        self.provider, self.binding = provider, dict(binding)
        self._token = token
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.reads = []

    def call(self, path, body=None):
        if (not isinstance(path, str) or not path.startswith("/") or path.startswith("//")
                or ".." in path or "#" in path or "\\" in path or any(c in path for c in "\r\n\0")):
            raise ValueError("FIXED_PROVIDER_API_PATH_REQUIRED")
        if body is not None and not (path == "/droplets" and self.provider == "digitalocean"
                or path == "/servers" and self.provider == "hetzner"
                or re.fullmatch(r"/datacenters/[A-Za-z0-9-]+/servers", path) and self.provider == "ionos"):
            raise ValueError("ONLY_BOUND_SERVER_CREATE_SUPPORTED")
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json", "Cache-Control": "no-cache"}
        if self.provider == "ionos": headers["X-Contract-Number"] = identifier(self.binding["principal_id"])
        request = urllib.request.Request(self.base + path, data=wire(body) if body is not None else None,
                                         headers=headers, method="POST" if body is not None else "GET")
        if body is not None: request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request, timeout=15) as response:
                if response.geturl() != self.base + path: raise ProviderError(0, "HOLD_PROVIDER_REDIRECT_FORBIDDEN")
                data = response.read(MAX_RESPONSE + 1)
                if len(data) > MAX_RESPONSE: raise ValueError("PROVIDER_RESPONSE_SIZE_LIMIT")
                if not 200 <= response.status < 300: raise ProviderError(response.status, "HOLD_PROVIDER_HTTP")
                result = decode(data)
        except urllib.error.HTTPError as exc:
            # Provider bodies stay private; only classify a narrow observed cause.
            message = exc.read(65536).decode("utf-8", errors="replace").lower()
            cause = ("HOLD_PAYMENT_METHOD_REQUIRED" if exc.code == 403 and "payment" in message
                     else "HOLD_PROVIDER_AUTHENTICATION" if exc.code == 401
                     else "HOLD_PROVIDER_PERMISSION" if exc.code == 403
                     else "HOLD_PROVIDER_RATE_LIMIT" if exc.code == 429 else "HOLD_PROVIDER_HTTP")
            raise ProviderError(exc.code, cause) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderError(0, "HOLD_PROVIDER_TRANSPORT_OUTCOME_UNKNOWN") from None
        if not isinstance(result, dict): raise ValueError("PROVIDER_OBJECT_RESPONSE_REQUIRED")
        self.reads.append({"method": request.method, "path": path, "response_sha256": sha(data)})
        return result

    def collection(self, path, key, ionos=False):
        result, seen = [], set()
        for page in range(1, MAX_PAGES + 1):
            sep = "&" if "?" in path else "?"
            url = path + sep + ("limit=1000&offset=" + str((page - 1) * 1000) if ionos else "per_page=200&page=" + str(page))
            response = self.call(url)
            items = response.get(key)
            if not isinstance(items, list): raise ValueError("HOLD_PROVIDER_INVENTORY_SHAPE")
            for item in items:
                if not isinstance(item, dict): raise ValueError("HOLD_PROVIDER_INVENTORY_SHAPE")
                item_id = catalog_id(item.get("id", item.get("slug")))
                if item_id in seen: raise ValueError("HOLD_PROVIDER_INVENTORY_DUPLICATE_OR_UNSTABLE")
                seen.add(item_id); result.append(item)
            if ionos:
                next_page = response.get("_links", {}).get("next")
                more = bool(next_page) or len(items) == 1000
            elif self.provider == "hetzner":
                pagination = response.get("meta", {}).get("pagination")
                if not isinstance(pagination, dict) or "next_page" not in pagination:
                    raise ValueError("HOLD_PROVIDER_PAGINATION_UNBOUND")
                more = pagination["next_page"] is not None
                if more and pagination["next_page"] != page + 1: raise ValueError("HOLD_PROVIDER_PAGINATION_CHANGED")
            else:
                total = response.get("meta", {}).get("total")
                if type(total) is not int or total < len(result): raise ValueError("HOLD_PROVIDER_PAGINATION_UNBOUND")
                more = bool(response.get("links", {}).get("pages", {}).get("next")) or len(result) < total
                if not more and len(result) != total: raise ValueError("HOLD_PROVIDER_PAGINATION_CHANGED")
            if not more: return result
            if not items: raise ValueError("HOLD_PROVIDER_PAGINATION_INCOMPLETE")
        raise ValueError("HOLD_PROVIDER_INVENTORY_PAGE_LIMIT")


def resource(provider, value, datacenter=None, location=None):
    """Whitelisted metadata only: never retain image passwords, user-data or tokens."""
    key = identifier(value["id"])
    if provider == "digitalocean":
        props = value
        ips = [i.get("ip_address") for i in value.get("networks", {}).get("v4", []) if i.get("type") == "public"]
        region = value.get("region", {}).get("slug")
        size = value.get("size_slug", value.get("size", {}).get("slug"))
        state = value.get("status")
    elif provider == "hetzner":
        props = value
        ip = value.get("public_net", {}).get("ipv4")
        ips = [ip.get("ip")] if isinstance(ip, dict) else []
        region = value.get("location", {}).get("name")
        size = value.get("server_type", {}).get("name")
        state = value.get("status")
    else:
        props = value.get("properties", {})
        ips = [ip for nic in value.get("entities", {}).get("nics", {}).get("items", [])
               for ip in nic.get("properties", {}).get("ips", [])]
        region, size = location, props.get("templateUuid") or "spec:" + sha(wire({k: props.get(k) for k in ("type", "cores", "ram")}))
        state = "running" if value.get("metadata", {}).get("state") == "AVAILABLE" and props.get("vmState") == "RUNNING" else props.get("vmState")
    valid_ips = []
    for address in ips:
        try: valid_ips.append(ipv4(address))
        except ValueError: pass
    result = {"id": key, "name": props.get("name"), "region": region, "size": size,
              "state": state, "public_ipv4": sorted(set(valid_ips)), "datacenter_id": datacenter}
    if provider == "ionos":
        result["compute"] = {k: props.get(k) for k in ("type", "cores", "ram")}
        result["disks"] = [{k: disk.get("properties", {}).get(k) for k in ("size", "type", "image")}
                           for disk in value.get("entities", {}).get("volumes", {}).get("items", [])]
        result["lans"] = sorted({str(nic.get("properties", {}).get("lan")) for nic in value.get("entities", {}).get("nics", {}).get("items", [])})
    return result


def ionos_resource_matches(observed, request):
    spec = request["ionos_spec"]
    return (observed["compute"] == {"type": "VCPU", "cores": spec["cores"], "ram": spec["ram_mb"]}
            and str(observed["datacenter_id"]) == str(spec["datacenter_id"])
            and str(spec["lan_id"]) in observed["lans"]
            and {"size": spec["disk_gb"], "type": spec["disk_type"], "image": request["image"]} in observed["disks"])


def collect(api, local_public_key=None):
    """Inventory precedes account/catalog/key planning; unknown resources are retained."""
    provider = api.provider
    snapshot = {"schema": SNAPSHOT, "provider": provider, "product": PRODUCTS[provider][0],
                "observer": "LIVE_FIXED_ORIGIN_API", "control_plane_bound": True, "authenticated": False,
                "principal_sha256": sha(wire({"provider": provider, "principal_id": api.binding["principal_id"]})),
                "complete": False, "resources": [], "keys": [], "regions": [], "sizes": [],
                "images": [], "pricing": None, "datacenters": [], "account": {"status": "UNKNOWN"},
                "started_at": timestamp(), "effect_ack_done": False}
    if provider == "digitalocean":
        normal = api.collection("/droplets?type=droplets", "droplets")
        gpu = api.collection("/droplets?type=gpus", "droplets")
        ids = [identifier(v["id"]) for v in normal + gpu]
        if len(ids) != len(set(ids)): raise ValueError("HOLD_PROVIDER_INVENTORY_DUPLICATE_OR_UNSTABLE")
        snapshot["resources"] = [resource(provider, v) for v in normal + gpu]
        account = api.call("/account")["account"]
        principal = account.get("team", {}).get("uuid") or account.get("uuid")
        if principal != api.binding["principal_id"]: raise ValueError("HOLD_PROVIDER_PRINCIPAL_MISMATCH")
        snapshot["account"] = {"status": account.get("status"), "message": account.get("status_message", ""), "resource_limit": account.get("droplet_limit")}
        key_values = api.collection("/account/keys", "ssh_keys")
        snapshot["regions"] = api.collection("/regions", "regions")
        snapshot["sizes"] = api.collection("/sizes", "sizes")
        snapshot["images"] = api.collection("/images?type=distribution", "images")
    elif provider == "hetzner":
        snapshot["resources"] = [resource(provider, v) for v in api.collection("/servers", "servers")]
        key_values = api.collection("/ssh_keys", "ssh_keys")
        snapshot["regions"] = api.collection("/locations", "locations")
        snapshot["sizes"] = api.collection("/server_types", "server_types")
        snapshot["images"] = api.collection("/images?type=system", "images")
        snapshot["pricing"] = api.call("/pricing")["pricing"]
        snapshot["account"] = {"status": "API_READ_ADMITTED", "message": "Project scope supplied through independently pinned binding; payment/terms/quota not inferred.", "resource_limit": None}
    else:
        datacenters = api.collection("/datacenters?depth=1", "items", ionos=True)
        for dc in datacenters:
            dcid = identifier(dc["id"]); location = dc.get("properties", {}).get("location")
            servers = api.collection("/datacenters/" + dcid + "/servers?depth=3", "items", ionos=True)
            lans = api.collection("/datacenters/" + dcid + "/lans?depth=1", "items", ionos=True)
            snapshot["datacenters"].append({"id": dcid, "region": location,
                "public_lans": [identifier(l["id"]) for l in lans if l.get("properties", {}).get("public") is True]})
            snapshot["resources"].extend(resource(provider, v, dcid, location) for v in servers)
        contracts = api.call("/contracts?depth=1")
        snapshot["account"] = {"status": "API_READ_ADMITTED", "resource_limit": None,
                               "contract_response_sha256": sha(wire(contracts)), "message": "Existing exact Cloud contract required; payment and terms are not inferred."}
        snapshot["regions"] = api.collection("/locations?depth=1", "items", ionos=True)
        snapshot["sizes"] = api.collection("/templates?depth=1", "items", ionos=True)
        snapshot["images"] = api.collection("/images?depth=1", "items", ionos=True)
        key_values = []  # CloudAPI volumes hide sshKeys on GET; do not invent a key-list API.
        if local_public_key is not None:
            key = public_key(local_public_key)
            snapshot["keys"].append(dict(key, id="local-public-key:" + key["sha256"], source="PINNED_EXISTING_OPERATOR_PUBLIC_KEY"))
    for key in key_values:
        snapshot["keys"].append(dict(public_key(key["public_key"]), id=identifier(key["id"]), source="EXISTING_PROVIDER_PUBLIC_KEY"))
    snapshot["images"] = [{k: image[k] for k in ("id", "name", "slug", "regions", "status", "type", "architecture", "deprecation") if k in image}
                          for image in snapshot["images"]]
    snapshot.update(authenticated=True, complete=True, completed_at=timestamp(), reads=list(api.reads))
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(value):
    if (not isinstance(value, dict) or value.get("schema") != SNAPSHOT or value.get("provider") not in PRODUCTS
            or value.get("product") != PRODUCTS[value["provider"]][0]
            or value.get("effect_ack_done") is not False):
        raise ValueError("EXACT_PROVIDER_INVENTORY_REQUIRED")
    for key in ("resources", "keys", "regions", "sizes", "images", "datacenters", "reads"):
        if not isinstance(value.get(key), list): raise ValueError("HOLD_PROVIDER_INVENTORY_SHAPE")
    pin(value.get("principal_sha256"))
    if not isinstance(value.get("account"), dict): raise ValueError("HOLD_PROVIDER_ACCOUNT_SHAPE")
    ids = [identifier(v["id"]) for v in value["resources"]]
    if len(ids) != len(set(ids)): raise ValueError("HOLD_PROVIDER_INVENTORY_DUPLICATE_OR_UNSTABLE")
    key_ids = []
    for key in value["keys"]:
        key_ids.append(identifier(key["id"]))
        if public_key(key["public_key"])["sha256"] != key["sha256"]:
            raise ValueError("HOLD_PROVIDER_PUBLIC_KEY_MISMATCH")
    if len(key_ids) != len(set(key_ids)): raise ValueError("HOLD_PROVIDER_KEY_INVENTORY_CONFLICT")
    fresh(value["completed_at"])
    fresh(value["started_at"])
    if instant(value["started_at"]) > instant(value["completed_at"]): raise ValueError("HOLD_PROVIDER_OBSERVATION_TIME_ORDER")
    return value


def classify(snapshot):
    validate_snapshot(snapshot)
    account = snapshot["account"]
    limit = account.get("resource_limit")
    if (type(limit) is int and len(snapshot["resources"]) < limit
            and re.search(r"maximum.*(?:droplet|server)|limit.*reached", account.get("message", ""), re.I)):
        return "HOLD_PROVIDER_ACCOUNT_INVENTORY_CONFLICT"
    if snapshot.get("control_plane_bound") is not True: return "HOLD_EXACT_PROVIDER_PRODUCT_AND_PRINCIPAL_BINDING_REQUIRED"
    if snapshot.get("authenticated") is not True: return "HOLD_PROVIDER_CREDENTIAL_UNBOUND"
    if account.get("status") not in {"active", "API_READ_ADMITTED"}: return "HOLD_PROVIDER_ACCOUNT_NOT_ADMITTED"
    if snapshot.get("complete") is not True: return "HOLD_PROVIDER_INVENTORY_INCOMPLETE"
    if limit is not None and (type(limit) is not int or limit < len(snapshot["resources"])):
        return "HOLD_PROVIDER_QUOTA_INVENTORY_CONFLICT"
    return None


def request_binding(request):
    fields = {"schema", "operation_id", "provider", "node_id", "source_repository", "source_head", "source_tree",
              "manifest_sha256", "config_sha256", "principal_sha256", "region", "size", "image", "resource_id",
              "ssh_key_sha256", "public_origin", "budget", "ionos_spec"}
    if not isinstance(request, dict) or set(request) != fields or request.get("schema") != REQUEST:
        raise ValueError("EXACT_PROVIDER_ADMISSION_REQUEST_REQUIRED")
    for k in ("operation_id", "node_id", "size", "image"): identifier(request[k])
    catalog_id(request["region"])
    if request["provider"] not in PRODUCTS: raise ValueError("SUPPORTED_PROVIDER_REQUIRED")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", request["source_repository"]):
        raise ValueError("EXACT_PROVIDER_SOURCE_REQUIRED")
    for k in ("source_head", "source_tree"):
        if not re.fullmatch(r"[a-f0-9]{40}", request[k]): raise ValueError("EXACT_PROVIDER_SOURCE_REQUIRED")
    for k in ("manifest_sha256", "config_sha256", "principal_sha256", "ssh_key_sha256"): pin(request[k])
    if request["resource_id"] is not None: identifier(request["resource_id"])
    origin(request["public_origin"])
    return sha(wire(request))


def quote(snapshot, request, external_quote=None):
    provider, region, size = request["provider"], request["region"], request["size"]
    if provider == "digitalocean":
        locations = [v for v in snapshot["regions"] if v.get("slug") == region and v.get("available") is True and size in v.get("sizes", [])]
        offers = [v for v in snapshot["sizes"] if v.get("slug") == size and v.get("available") is True and region in v.get("regions", [])]
        if len(locations) != 1 or len(offers) != 1: raise ValueError("HOLD_REGION_SIZE_UNAVAILABLE_OR_AMBIGUOUS")
        offer = offers[0]
        result = {"currency": "USD", "hourly": str(money(offer["price_hourly"])), "monthly": str(money(offer["price_monthly"])),
                  "basis": "PROVIDER_NET_BASE_COMPUTE_BOOT_DISK_PUBLIC_IPV4_NO_BACKUPS",
                  "included_transfer_tb": offer.get("transfer"), "variable_usage_and_tax_capped": False}
    elif provider == "hetzner":
        locations = [v for v in snapshot["regions"] if v.get("name") == region]
        offers = [v for v in snapshot["sizes"] if v.get("name") == size]
        if len(locations) != 1 or len(offers) != 1: raise ValueError("HOLD_REGION_SIZE_UNAVAILABLE_OR_AMBIGUOUS")
        availability = [v for v in offers[0].get("locations", []) if v.get("name") == region and v.get("deprecation") is None]
        if len(availability) != 1: raise ValueError("HOLD_REGION_SIZE_UNAVAILABLE_OR_AMBIGUOUS")
        pricing = snapshot["pricing"]
        server = [v for v in pricing["server_types"] if v.get("name") == size]
        ips = [v for v in pricing["primary_ips"] if v.get("type") == "ipv4"]
        if len(server) != 1 or len(ips) != 1: raise ValueError("HOLD_COMPLETE_COMPUTE_AND_IPV4_QUOTE_REQUIRED")
        def price(item):
            matches = [v for v in item["prices"] if v.get("location") == region]
            if len(matches) != 1: raise ValueError("HOLD_COMPLETE_COMPUTE_AND_IPV4_QUOTE_REQUIRED")
            return matches[0]
        server_price, ip_price = price(server[0]), price(ips[0])
        result = {"currency": pricing["currency"],
                  "hourly": str(money(server_price["price_hourly"]["gross"]) + money(ip_price["price_hourly"]["gross"])),
                  "monthly": str(money(server_price["price_monthly"]["gross"]) + money(ip_price["price_monthly"]["gross"])),
                  "basis": "PROJECT_GROSS_COMPUTE_BOOT_DISK_PLUS_PRIMARY_IPV4_NO_BACKUPS",
                  "variable_usage_and_tax_capped": False}
    else:
        spec = request["ionos_spec"]
        required = {"datacenter_id", "lan_id", "cores", "ram_mb", "disk_gb", "disk_type"}
        if (not isinstance(spec, dict) or set(spec) != required or any(type(spec[k]) is not int or spec[k] <= 0 for k in ("cores", "ram_mb", "disk_gb"))
                or spec["disk_type"] not in {"HDD", "SSD", "SSD Standard", "SSD Premium"}):
            raise ValueError("HOLD_EXACT_IONOS_CLOUD_SPEC_REQUIRED")
        expected_size = "spec:" + sha(wire({"type": "VCPU", "cores": spec["cores"], "ram": spec["ram_mb"]}))
        if size != expected_size: raise ValueError("HOLD_EXACT_IONOS_CLOUD_SPEC_REQUIRED")
        centers = [v for v in snapshot["datacenters"] if v["id"] == identifier(spec["datacenter_id"]) and v["region"] == region
                   and identifier(spec["lan_id"]) in v["public_lans"]]
        if len(centers) != 1: raise ValueError("HOLD_EXISTING_IONOS_DATACENTER_AND_PUBLIC_LAN_REQUIRED")
        if (not isinstance(external_quote, dict) or external_quote.get("provider") != provider
                or external_quote.get("principal_sha256") != request["principal_sha256"]
                or external_quote.get("region") != region or external_quote.get("size") != size
                or external_quote.get("ionos_spec") != spec or external_quote.get("image") != request["image"]
                or external_quote.get("coverage") != ["compute", "boot_disk", "public_ipv4"]):
            raise ValueError("HOLD_INDEPENDENT_IONOS_CONTRACT_PRICE_QUOTE_REQUIRED")
        pin(external_quote.get("source_evidence_sha256"))
        if instant(external_quote["expires_at"]) <= dt.datetime.now(dt.timezone.utc): raise ValueError("HOLD_COST_QUOTE_EXPIRED")
        result = {k: external_quote[k] for k in ("currency", "hourly", "monthly", "basis")}
        money(result["hourly"]); money(result["monthly"])
        result.update(source_evidence_sha256=external_quote["source_evidence_sha256"], variable_usage_and_tax_capped=False)
    if not re.fullmatch(r"[A-Z]{3}", result["currency"]): raise ValueError("PROVIDER_CURRENCY_REQUIRED")
    return dict(result, provider=provider, region=region, size=size)


def plan(snapshot, request, external_quote=None):
    request_sha = request_binding(request)
    validate_snapshot(snapshot)
    if snapshot["provider"] != request["provider"] or snapshot["principal_sha256"] != request["principal_sha256"]:
        raise ValueError("HOLD_PROVIDER_REQUEST_PRINCIPAL_MISMATCH")
    stable_inventory = {k: v for k, v in snapshot.items() if k not in {"started_at", "completed_at", "reads"}}
    result = {"schema": "qikvrt-provider-admission-plan/v1", "request_sha256": request_sha,
              "inventory_sha256": sha(wire(snapshot)), "state": "HOLD", "first_boundary": classify(snapshot),
              "inventory_binding_sha256": sha(wire(stable_inventory)),
              "unknown_resources_retained": [v["id"] for v in snapshot["resources"]],
              "provider_create_executed": False, "host_admission_verified": False, "public_readback_verified": False,
              "effect_ack_done": False}
    if result["first_boundary"]: return result
    try:
        cost = quote(snapshot, request, external_quote)
        result.update(cost_quote=cost, cost_quote_sha256=sha(wire(cost)))
        keys = [k for k in snapshot["keys"] if k.get("sha256") == request["ssh_key_sha256"]]
        if not keys: raise ValueError("HOLD_EXISTING_PUBLIC_SSH_KEY_REQUIRED")
        for k in keys:
            if public_key(k["public_key"])["sha256"] != request["ssh_key_sha256"]: raise ValueError("HOLD_PROVIDER_PUBLIC_KEY_MISMATCH")
        key = sorted(keys, key=lambda k: k["id"])[0]
        result["ssh_key"] = {k: key[k] for k in ("id", "sha256", "source")}
        budget = request["budget"]
        if (not isinstance(budget, dict) or set(budget) != {"currency", "max_hourly", "max_monthly", "variable_usage_authorized"}
                or budget["currency"] != cost["currency"]):
            raise ValueError("HOLD_COST_BUDGET_BINDING_REQUIRED")
        if money(cost["hourly"]) > money(budget["max_hourly"]) or money(cost["monthly"]) > money(budget["max_monthly"]):
            raise ValueError("HOLD_COST_QUOTE_EXCEEDS_AUTHORIZED_BUDGET")
        if budget["variable_usage_authorized"] is not True: raise ValueError("HOLD_VARIABLE_USAGE_COST_AUTHORIZATION_REQUIRED")
        operation_name = "qikvrt-" + sha(wire({"operation_id": request["operation_id"], "node_id": request["node_id"]}))[:32]
        matches = [v for v in snapshot["resources"] if v["id"] == str(request["resource_id"])] if request["resource_id"] is not None else []
        if request["resource_id"] is not None and len(matches) != 1: raise ValueError("HOLD_EXPLICIT_REUSE_RESOURCE_NOT_FOUND")
        if matches:
            selected = matches[0]
            if selected["region"] != request["region"] or selected["size"] != request["size"]:
                raise ValueError("HOLD_REUSE_REGION_SIZE_MISMATCH")
            if request["provider"] == "ionos" and not ionos_resource_matches(selected, request):
                raise ValueError("HOLD_REUSE_IONOS_SPEC_MISMATCH")
            result.update(action="reuse", resource=selected, state="REUSE_PLAN_BOUND_PENDING_HEALTH")
        else:
            if any(v["name"] == operation_name for v in snapshot["resources"]): raise ValueError("HOLD_EXISTING_OPERATION_RESOURCE_REQUIRES_RECONCILIATION")
            limit = snapshot["account"].get("resource_limit")
            if type(limit) is int and len(snapshot["resources"]) >= limit: raise ValueError("HOLD_PROVIDER_RESOURCE_LIMIT")
            image_keys = ("slug",) if request["provider"] == "digitalocean" else ("name", "id")
            images = [v for v in snapshot["images"] if any(str(v.get(k)) == request["image"] for k in image_keys)]
            if len(images) != 1: raise ValueError("HOLD_EXACT_PROVIDER_IMAGE_REQUIRED")
            image = images[0]
            if request["provider"] == "digitalocean" and request["region"] not in image.get("regions", []):
                raise ValueError("HOLD_PROVIDER_IMAGE_REGION_UNAVAILABLE")
            result.update(action="create", operation_name=operation_name, state="CREATE_PLAN_BOUND_PENDING_AUTHORIZATION")
            provider = request["provider"]
            if provider == "digitalocean":
                path, body = "/droplets", {"name": operation_name, "region": request["region"], "size": request["size"],
                    "image": request["image"], "ssh_keys": [key["id"]], "backups": False, "ipv6": False, "monitoring": True}
            elif provider == "hetzner":
                path, body = "/servers", {"name": operation_name, "location": request["region"], "server_type": request["size"],
                    "image": request["image"], "ssh_keys": [int(key["id"])], "public_net": {"enable_ipv4": True, "enable_ipv6": False}}
            else:
                spec = request["ionos_spec"]
                path = "/datacenters/" + identifier(spec["datacenter_id"]) + "/servers"
                body = {"properties": {"name": operation_name, "type": "VCPU", "cores": spec["cores"], "ram": spec["ram_mb"]},
                    "entities": {"volumes": {"items": [{"properties": {"name": operation_name + "-boot", "size": spec["disk_gb"],
                        "type": spec["disk_type"], "image": request["image"], "sshKeys": [key["public_key"]]}}]},
                        "nics": {"items": [{"properties": {"name": operation_name + "-nic", "dhcp": True, "lan": int(spec["lan_id"])}}]}}}
            result["provider_operation"] = {"method": "POST", "path": path, "body": body}
        result["first_boundary"] = None
        result["admission_sha256"] = sha(wire({k: result[k] for k in ("request_sha256", "inventory_binding_sha256", "cost_quote_sha256", "ssh_key", "action")}))
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        result["state"] = "HOLD"
        result["first_boundary"] = str(exc) if isinstance(exc, ValueError) else "HOLD_PROVIDER_CATALOG_OR_BINDING_SHAPE"
    return result


class Receipts:
    """Reuse S1 private/fsync primitives; immutable receipts, not another event ledger."""
    def __init__(self, directory):
        self.directory = directory
        host.private_path(directory, directory=True)

    @contextlib.contextmanager
    def locked(self):
        path = self.directory / "provider-admission.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as lock:
            host.private_path(path)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def path(self, operation_id, stage):
        identifier(operation_id)
        if not re.fullmatch(r"[a-z0-9-]{1,100}", stage): raise ValueError("RECEIPT_STAGE_REQUIRED")
        return self.directory / (sha(operation_id.encode()) + "." + stage + ".json")

    def get(self, operation_id, stage):
        path = self.path(operation_id, stage)
        if not path.exists(): return None
        host.private_path(path)
        return decode(path.read_bytes())

    def put(self, operation_id, stage, value):
        path, data = self.path(operation_id, stage), wire(value)
        if path.exists():
            host.private_path(path)
            if path.read_bytes() != data: raise ValueError("HOLD_OPERATION_RECEIPT_CONFLICT")
        else:
            host.synced_private_file(path, data); host.sync_directory(self.directory)
        return sha(data)


def authorize(grant, admission, request):
    required = {"schema", "decision", "request_sha256", "admission_sha256", "cost_quote_sha256", "principal_sha256",
                "expires_at", "payment_evidence_sha256", "accepted_terms_evidence_sha256", "authorization_evidence_sha256", "effects"}
    if (not isinstance(grant, dict) or set(grant) != required or grant["schema"] != "qikvrt-exact-provider-create-authorization/v1"
            or grant["decision"] != "AUTHORIZE_EXACT_CREATE" or grant["request_sha256"] != admission["request_sha256"]
            or grant["admission_sha256"] != admission["admission_sha256"] or grant["cost_quote_sha256"] != admission["cost_quote_sha256"]
            or grant["principal_sha256"] != request["principal_sha256"]
            or grant["effects"] != ["server_create", "boot_disk_create", "public_ipv4_allocate"]):
        raise ValueError("HOLD_EXACT_CREATE_AUTHORIZATION_REQUIRED")
    for k in ("payment_evidence_sha256", "accepted_terms_evidence_sha256", "authorization_evidence_sha256"): pin(grant[k])
    if instant(grant["expires_at"]) <= dt.datetime.now(dt.timezone.utc): raise ValueError("HOLD_CREATE_AUTHORIZATION_EXPIRED")


def get_resource(api, resource_id, request):
    rid = identifier(resource_id)
    if api.provider == "digitalocean": value = api.call("/droplets/" + rid)["droplet"]
    elif api.provider == "hetzner": value = api.call("/servers/" + rid)["server"]
    else:
        dc = identifier(request["ionos_spec"]["datacenter_id"])
        value = api.call("/datacenters/" + dc + "/servers/" + rid + "?depth=3")
    observed = resource(api.provider, value, request.get("ionos_spec", {}).get("datacenter_id") if request.get("ionos_spec") else None, request["region"])
    if observed["id"] != rid: raise ValueError("HOLD_PROVIDER_RESOURCE_ID_MISMATCH")
    return observed


def reconcile(api, request, receipts, snapshot=None):
    if (api.provider != request["provider"] or sha(wire({"provider": api.provider, "principal_id": api.binding["principal_id"]})) != request["principal_sha256"]):
        raise ValueError("HOLD_PROVIDER_REQUEST_PRINCIPAL_MISMATCH")
    intent = receipts.get(request["operation_id"], "intent")
    if not intent or intent["request_sha256"] != request_binding(request): raise ValueError("HOLD_OPERATION_ID_CONFLICT")
    transport = receipts.get(request["operation_id"], "transport")
    rid = transport.get("resource_id") if transport else None
    if rid is None:
        snapshot = snapshot or collect(api)
        boundary = classify(snapshot)
        if boundary: raise ValueError(boundary)
        matches = [v for v in snapshot["resources"] if v["name"] == intent["operation_name"]]
        if len(matches) != 1:
            return {"state": "HOLD_CREATE_OUTCOME_UNKNOWN_READBACK_ONLY", "request_sha256": intent["request_sha256"],
                    "create_retry_permitted": False, "effect_ack_done": False}
        rid = matches[0]["id"]
    observed = get_resource(api, rid, request)
    if (observed["name"] != intent["operation_name"] or observed["region"] != request["region"]
            or api.provider != "ionos" and observed["size"] != request["size"]):
        raise ValueError("HOLD_PROVIDER_CREATED_RESOURCE_BINDING_MISMATCH")
    if api.provider == "ionos" and not ionos_resource_matches(observed, request):
        raise ValueError("HOLD_PROVIDER_CREATED_RESOURCE_BINDING_MISMATCH")
    readback = {"schema": "qikvrt-provider-operation-readback/v1", "request_sha256": intent["request_sha256"],
                "resource": observed, "create_retry_permitted": False,
                "scope": "PROVIDER_METADATA_ONLY; CREATING_PRINCIPAL_AND_SSH_INJECTION_NOT_INDEPENDENTLY_PROVED",
                "effect_ack_done": False}
    receipts.put(request["operation_id"], "readback-" + sha(wire(readback)), readback)
    return dict(readback, state="OPERATION_READBACK_QUITTED_PENDING_IPV4_HTTPS_AND_INDEPENDENT_CLIENT")


def apply(api, request, receipts, grant=None, external_quote=None, local_public_key=None):
    request_sha = request_binding(request)
    with receipts.locked():
        receipts.put(request["operation_id"], "request", {"request_sha256": request_sha, "effect_ack_done": False})
        intent = receipts.get(request["operation_id"], "intent")
        if intent:
            if intent["request_sha256"] != request_sha: raise ValueError("HOLD_OPERATION_ID_CONFLICT")
            return reconcile(api, request, receipts)
        snapshot = collect(api, local_public_key)  # fresh reads immediately before any effect
        admission = plan(snapshot, request, external_quote)
        if admission["first_boundary"]: return admission
        if admission["action"] == "reuse":
            observed = get_resource(api, admission["resource"]["id"], request)
            if observed != admission["resource"]: raise ValueError("HOLD_REUSE_RESOURCE_CHANGED_AFTER_INVENTORY")
            receipt = {"schema": "qikvrt-provider-reuse-receipt/v1", "request_sha256": request_sha,
                       "resource": observed, "effect_ack_done": False}
            receipts.put(request["operation_id"], "reuse-" + sha(wire(receipt)), receipt)
            return dict(receipt, state="EXISTING_RESOURCE_REUSED_PENDING_PUBLIC_READBACK", provider_create_executed=False)
        authorize(grant, admission, request)
        if snapshot["observer"] != "LIVE_FIXED_ORIGIN_API": raise ValueError("HOLD_LIVE_CONTROL_PLANE_REQUIRED_FOR_CREATE")
        intent = {"schema": "qikvrt-provider-create-intent/v1", "request_sha256": request_sha,
                  "admission_sha256": admission["admission_sha256"], "operation_name": admission["operation_name"],
                  "provider_operation_sha256": sha(wire(admission["provider_operation"])),
                  "authorization_sha256": sha(wire(grant)), "effect_ack_done": False}
        receipts.put(request["operation_id"], "intent", intent)  # durable before POST, never removed
        operation = admission["provider_operation"]
        try:
            response = api.call(operation["path"], operation["body"])
            value = response.get("droplet") if api.provider == "digitalocean" else response.get("server") if api.provider == "hetzner" else response
            transport = {"resource_id": identifier(value["id"]), "action_id": response.get("action", {}).get("id"),
                         "request_sha256": request_sha, "state": "TRANSPORT_ACK_ONLY", "effect_ack_done": False}
        except (ValueError, OSError, KeyError, TypeError) as exc:
            transport = {"resource_id": None, "request_sha256": request_sha, "state": "OUTCOME_UNKNOWN_OR_REJECTED_READBACK_ONLY",
                         "http_status": exc.status if isinstance(exc, ProviderError) else None,
                         "cause": exc.cause if isinstance(exc, ProviderError) else "HOLD_CREATE_OUTCOME_UNKNOWN",
                         "effect_ack_done": False}
        receipts.put(request["operation_id"], "transport", transport)
        return reconcile(api, request, receipts)


def https_health(request, observed):
    """IPv4-pinned TLS with normal CA/SNI validation, no redirects or provider token."""
    if observed["state"] not in {"active", "running"}: raise ValueError("HOLD_PROVIDER_RESOURCE_NOT_RUNNING")
    name = origin(request["public_origin"])
    candidates = set(observed["public_ipv4"])
    if not candidates: raise ValueError("HOLD_PUBLIC_IPV4_UNAVAILABLE")
    addresses = {ipv4(v[4][0]) for v in socket.getaddrinfo(name, 443, socket.AF_INET, socket.SOCK_STREAM)}
    if not addresses or not addresses <= candidates: raise ValueError("HOLD_HTTPS_DNS_PROVIDER_IPV4_MISMATCH")
    address = sorted(addresses)[0]
    context = ssl.create_default_context()
    connection = http.client.HTTPSConnection(name, 443, timeout=15, context=context)
    try:
        plain = socket.create_connection((address, 443), timeout=15)
        try: connection.sock = context.wrap_socket(plain, server_hostname=name)
        except BaseException: plain.close(); raise
        connection.request("GET", "/health", headers={"Cache-Control": "no-cache"})
        response = connection.getresponse()
        data = response.read(MAX_RESPONSE + 1)
        if response.status != 200 or len(data) > MAX_RESPONSE: raise ValueError("HOLD_PUBLIC_HTTPS_HEALTH")
        health = decode(data)
        if (health.get("schema") != "qikvrt-monitor-binding/v1" or health.get("node_id") != request["node_id"]
                or any(health.get(k) != request[k] for k in ("source_repository", "source_head", "source_tree"))
                or health.get("health", {}).get("state") != "HEALTHY"):
            raise ValueError("HOLD_PUBLIC_HTTPS_SOURCE_OR_HEALTH_BINDING")
        fresh(health["observed_at"])
        return {"state": "IPV4_HTTPS_HEALTH_VERIFIED_PENDING_INDEPENDENT_READBACK", "public_origin": request["public_origin"],
                "ipv4": address, "health_sha256": sha(data), "readback_observed_at": timestamp(), "effect_ack_done": False}
    finally: connection.close()


def independent_readback(api, request, package, manifest_pin, config, receipts):
    snapshot = collect(api)
    boundary = classify(snapshot)
    if boundary: raise ValueError(boundary)
    if snapshot["principal_sha256"] != request["principal_sha256"]: raise ValueError("HOLD_PROVIDER_REQUEST_PRINCIPAL_MISMATCH")
    manifest = host.verify(package, manifest_pin)
    host.private_path(config)
    config_raw = config.read_bytes()
    configuration = decode(config_raw)
    if (manifest_pin != request["manifest_sha256"] or sha(config_raw) != request["config_sha256"]
            or any(manifest[k] != request[k] for k in ("source_repository", "source_head", "source_tree"))
            or configuration["node_id"] != request["node_id"] or configuration["adapter"] != "none"):
        raise ValueError("HOLD_PROVIDER_PACKAGE_CONFIGURATION_BINDING")
    if request["resource_id"] is None:
        with receipts.locked():
            result = reconcile(api, request, receipts)
        if "resource" not in result: return result
        rid = result["resource"]["id"]
    else: rid = request["resource_id"]
    before = get_resource(api, rid, request)
    if (before["region"] != request["region"] or before["size"] != request["size"]
            or api.provider == "ionos" and not ionos_resource_matches(before, request)):
        raise ValueError("HOLD_PROVIDER_RESOURCE_READBACK_BINDING_MISMATCH")
    health = https_health(request, before)
    argv = [host.shutil.which("node"), str(package / "tools/qikvrt_mesh_monitor_readback.mjs"), "--self-host",
            str(package), request["public_origin"], manifest_pin, request["config_sha256"], request["node_id"], "none", health["ipv4"]]
    # Existing verifier, separate bounded process; a successful GET alone cannot close this stage.
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TZ") if k in os.environ}
    completed = run_bounded(argv, env=env, timeout=120, max_output_bytes=MAX_RESPONSE)
    if completed.returncode or completed.timed_out or completed.output_limit_exceeded: raise ValueError("HOLD_INDEPENDENT_PUBLIC_CLIENT_READBACK")
    client = decode(completed.stdout)
    if (client.get("state") != "CLIENT_BYTE_READBACK_VERIFIED" or client.get("public_url") != request["public_origin"]
            or client.get("health_state") != "HEALTHY" or client.get("effect_ack_done") is not False
            or any(client.get(k) != request[k] for k in ("source_head", "source_tree"))):
        raise ValueError("HOLD_INDEPENDENT_PUBLIC_CLIENT_BINDING")
    fresh(client["readback_observed_at"])
    if get_resource(api, rid, request) != before: raise ValueError("HOLD_PROVIDER_RESOURCE_CHANGED_DURING_READBACK")
    receipt = {"schema": "qikvrt-provider-public-readback/v1", "request_sha256": request_binding(request),
               "resource": before, "health": health, "independent_client": client,
               "state": "PROVIDER_IPV4_HTTPS_AND_CLIENT_READBACK_VERIFIED_PENDING_NATIVE_HOST_ACCEPTANCE",
               "host_admission_verified": False, "deployed_restart_verified": False, "effect_ack_done": False}
    with receipts.locked(): receipts.put(request["operation_id"], "public-" + sha(wire(receipt)), receipt)
    return receipt


def api_from_args(args, api_class=API):
    if not args.provider_binding or not args.provider_binding_sha256:
        raise ValueError("HOLD_EXACT_PROVIDER_PRODUCT_AND_PRINCIPAL_BINDING_REQUIRED")
    binding = pinned(args.provider_binding, args.provider_binding_sha256)
    if args.provider_credential:
        host.private_path(args.provider_credential)
        if args.provider_credential.stat().st_size > 4096: raise ValueError("BOUNDED_PROVIDER_CREDENTIAL_REQUIRED")
        token = args.provider_credential.read_text().strip()
    else: token = os.environ.get(TOKEN_ENV[args.provider], "")
    return api_class(args.provider, token, binding)


def execute(args, api_class=API):
    if args.provider not in PRODUCTS: raise ValueError("SUPPORTED_PROVIDER_REQUIRED")
    local_key = None
    if args.provider_public_key:
        host.private_path(args.provider_public_key)
        data = args.provider_public_key.read_bytes()
        if sha(data) != pin(args.provider_public_key_sha256): raise ValueError("EXISTING_PUBLIC_KEY_PIN_MISMATCH")
        local_key = data.decode().strip()
        public_key(local_key)
    external_quote = pinned(args.provider_quote, args.provider_quote_sha256) if args.provider_quote else None
    if args.operation == "provider-inventory":
        value = collect(api_from_args(args, api_class), local_key)
        if args.output:
            host.private_output(args.output, [args.root.resolve()])
            host.synced_private_file(args.output, wire(value)); host.sync_directory(args.output.parent)
        return value
    if args.operation == "provider-classify":
        value = pinned(args.provider_inventory, args.provider_inventory_sha256)
        if value.get("provider") != args.provider: raise ValueError("HOLD_REQUEST_PROVIDER_MISMATCH")
        boundary = classify(value)
        return {"state": "HOLD" if boundary else "INVENTORY_READ_ADMITTED_PENDING_REQUEST_BINDING",
                "first_boundary": boundary, "inventory_sha256": sha(wire(value)),
                "resources_returned": len(value["resources"]), "account": value["account"],
                "provider_create_executed": False, "effect_ack_done": False}
    request = pinned(args.provider_request, args.provider_request_sha256)
    request_binding(request)
    if request["provider"] != args.provider: raise ValueError("HOLD_REQUEST_PROVIDER_MISMATCH")
    if args.operation == "provider-plan":
        snapshot = pinned(args.provider_inventory, args.provider_inventory_sha256)
        return plan(snapshot, request, external_quote)
    api = api_from_args(args)
    if not args.provider_receipts: raise ValueError("SEPARATE_PRIVATE_PROVIDER_RECEIPTS_REQUIRED")
    package = args.root.resolve()
    if args.provider_receipts == package or package in args.provider_receipts.parents:
        raise ValueError("SEPARATE_PRIVATE_PROVIDER_RECEIPTS_REQUIRED")
    receipts = Receipts(args.provider_receipts)
    if args.operation == "provider-apply":
        manifest = host.verify(args.root.resolve(), args.manifest_sha256)
        if (args.manifest_sha256 != request["manifest_sha256"]
                or any(manifest[k] != request[k] for k in ("source_repository", "source_head", "source_tree"))
                or manifest["files"].get("tools/qikvrt_self_host_provider.py", {}).get("sha256") != sha(Path(__file__).read_bytes())):
            raise ValueError("HOLD_EXACT_PACKAGED_PROVIDER_EXECUTOR_REQUIRED")
        if args.config is None: raise ValueError("HOLD_EXACT_PROVIDER_CONFIGURATION_REQUIRED")
        host.private_path(args.config)
        config_raw = args.config.read_bytes()
        config = decode(config_raw)
        if (sha(config_raw) != request["config_sha256"] or config.get("node_id") != request["node_id"]
                or any(config.get(k) != request[k] for k in ("source_repository", "source_head", "source_tree"))):
            raise ValueError("HOLD_PROVIDER_PACKAGE_CONFIGURATION_BINDING")
        grant = pinned(args.provider_authorization, args.provider_authorization_sha256) if args.provider_authorization else None
        return apply(api, request, receipts, grant, external_quote, local_key)
    if args.operation == "provider-reconcile":
        with receipts.locked(): return reconcile(api, request, receipts)
    if args.operation == "provider-readback":
        return independent_readback(api, request, args.root.resolve(), args.manifest_sha256, args.config, receipts)


class ReadOnlyIONOSAPI(API):
    """Repository inventory capability: fixed IONOS GETs, no create capability."""
    def call(self, path, body=None):
        if self.provider != "ionos" or body is not None:
            raise ValueError("HOLD_IONOS_READONLY_OPERATION_REQUIRED")
        allowed = (r"/(?:locations|templates|images|datacenters)\?depth=1&limit=1000&offset=[0-9]+",
                   r"/datacenters/[A-Za-z0-9_.:-]+/servers\?depth=3&limit=1000&offset=[0-9]+",
                   r"/datacenters/[A-Za-z0-9_.:-]+/lans\?depth=1&limit=1000&offset=[0-9]+",
                   r"/contracts\?depth=1")
        if not any(re.fullmatch(pattern, path) for pattern in allowed):
            raise ValueError("HOLD_IONOS_READONLY_PATH_REQUIRED")
        result = super().call(path)
        if path == "/contracts?depth=1":
            items = result.get("items")
            if (not isinstance(items, list) or any(not isinstance(item, dict)
                    or not isinstance(item.get("properties"), dict) for item in items)):
                raise ValueError("HOLD_IONOS_CONTRACT_PRINCIPAL_UNCONFIRMED")
            matches = [item for item in items if type(item["properties"].get("contractNumber")) in (int, str)
                       and str(item["properties"]["contractNumber"]) == self.binding["principal_id"]]
            if len(matches) != 1:
                raise ValueError("HOLD_IONOS_CONTRACT_PRINCIPAL_UNCONFIRMED")
        return result


def repository_readonly(directory, subject):
    """Reuse both provider operations; persist only a bounded metadata receipt.

    An existing secret name and an independently supplied binding digest are
    required. Neither this wrapper nor its workflow creates or discovers secrets.
    Private binding/inventory bytes are temporary; exceptions are never echoed.
    """
    env = os.environ
    host.private_path(directory, directory=True)
    receipt_path = directory / "receipt.json"
    host.private_output(receipt_path, [host.ROOT])
    receipt = {"schema": "qikvrt-ionos-readonly-receipt/v1", "state": "HOLD",
               "first_boundary": None, "missing_bindings": [], "started_at": timestamp(),
               "operations": ["provider-inventory", "provider-classify"],
               "provider": "ionos", "origin": PRODUCTS["ionos"][1],
               "inventory_started": False, "inventory_completed": False,
               "classification_started": False, "classification_completed": False,
               "fresh_private_readback_verified": False, "provider_create_executed": False,
               "payment_executed": False, "terms_accepted": False, "effect_ack_done": False}
    safe_errors = {"HOLD_PROVIDER_REDIRECT_FORBIDDEN", "HOLD_PROVIDER_HTTP", "HOLD_PAYMENT_METHOD_REQUIRED",
                   "HOLD_PROVIDER_AUTHENTICATION", "HOLD_PROVIDER_PERMISSION", "HOLD_PROVIDER_RATE_LIMIT",
                   "HOLD_PROVIDER_TRANSPORT_OUTCOME_UNKNOWN", "HOLD_PROVIDER_CREDENTIAL_UNBOUND",
                   "HOLD_PROVIDER_INVENTORY_SHAPE", "HOLD_PROVIDER_INVENTORY_DUPLICATE_OR_UNSTABLE",
                   "HOLD_PROVIDER_PAGINATION_UNBOUND", "HOLD_PROVIDER_PAGINATION_CHANGED",
                   "HOLD_PROVIDER_PAGINATION_INCOMPLETE", "HOLD_PROVIDER_INVENTORY_PAGE_LIMIT",
                   "HOLD_PROVIDER_OBSERVATION_NOT_FRESH", "HOLD_PROVIDER_OBSERVATION_TIME_ORDER",
                   "HOLD_IONOS_READONLY_OPERATION_REQUIRED", "HOLD_IONOS_READONLY_PATH_REQUIRED",
                   "HOLD_IONOS_CONTRACT_PRINCIPAL_UNCONFIRMED", "PROVIDER_RESPONSE_SIZE_LIMIT",
                   "DUPLICATE_PROVIDER_JSON_KEY", "NONFINITE_PROVIDER_JSON", "PROVIDER_INPUT_PIN_MISMATCH"}
    try:
        if (not isinstance(subject, dict) or set(subject) != {"repository", "ref", "head", "tree", "run_id", "run_attempt"}
                or subject["repository"] != "ingolf-lohmann/qik-vrt" or subject["ref"] != "refs/heads/main"
                or any(not re.fullmatch(r"[a-f0-9]{40}", str(subject[key])) for key in ("head", "tree"))
                or any(not re.fullmatch(r"[1-9][0-9]*", str(subject[key])) for key in ("run_id", "run_attempt"))):
            receipt["missing_bindings"] = ["fresh exact main HEAD/TREE and native run subject"]
            raise ValueError("HOLD_IONOS_EXACT_SOURCE_SUBJECT_REQUIRED")
        receipt["subject"] = dict(subject)
        carrier = env.get("IONOS_BINDING_SECRET_NAME", "")
        text = env.get("IONOS_BINDING_JSON", "")
        binding_pin = env.get("IONOS_BINDING_SHA256", "")
        for condition, missing in (
                (not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,99}", carrier) or carrier.upper().startswith("GITHUB_"),
                 "existing repository secret name carrying PROVIDER_BINDING JSON"),
                (not text, "selected existing repository secret -> IONOS_BINDING_JSON delivery"),
                (not re.fullmatch(r"[a-f0-9]{64}", binding_pin) or binding_pin == "0" * 64,
                 "independent SHA-256 pin of exact PROVIDER_BINDING bytes"),
                (not env.get("IONOS_TOKEN"), "secrets.IONOS_TOKEN -> IONOS_TOKEN delivery")):
            if condition: receipt["missing_bindings"].append(missing)
        if receipt["missing_bindings"]:
            raise ValueError("HOLD_IONOS_READONLY_BINDING_UNAVAILABLE")
        raw = text.encode("utf-8")
        if len(raw) > 8192 or sha(raw) != binding_pin:
            raise ValueError("HOLD_IONOS_PROVIDER_BINDING_PIN_MISMATCH")
        binding = decode(raw)
        if (not isinstance(binding, dict) or set(binding) != {"product", "principal_id", "principal_evidence_sha256"}
                or binding["product"] != "ionos-cloud-v6"):
            receipt["missing_bindings"] = ["product=ionos-cloud-v6 in pinned PROVIDER_BINDING"]
            raise ValueError("HOLD_IONOS_PROVIDER_PRODUCT_BINDING_REQUIRED")
        if not isinstance(binding["principal_id"], str) or not re.fullmatch(r"[0-9]{1,20}", binding["principal_id"]):
            receipt["missing_bindings"].append("actual independently verified IONOS Cloud contract number as principal_id")
        evidence_pin = binding.get("principal_evidence_sha256")
        if not isinstance(evidence_pin, str) or not re.fullmatch(r"[a-f0-9]{64}", evidence_pin) or evidence_pin == "0" * 64:
            receipt["missing_bindings"].append("principal_evidence_sha256 for independently verified contract evidence")
        if receipt["missing_bindings"]:
            raise ValueError("HOLD_IONOS_CONTRACT_PRINCIPAL_BINDING_REQUIRED")
        receipt["binding_sha256"] = binding_pin
        with tempfile.TemporaryDirectory(prefix="ionos-private-", dir=directory.parent) as temporary:
            private = Path(temporary)
            binding_path, inventory_path = private / "binding.json", private / "inventory.json"
            host.synced_private_file(binding_path, raw)
            args = SimpleNamespace(operation="provider-inventory", provider="ionos", root=host.ROOT,
                    provider_binding=binding_path, provider_binding_sha256=binding_pin, provider_credential=None,
                    provider_public_key=None, provider_quote=None, output=inventory_path)
            # The workflow supplies IONOS_TOKEN only to this single bounded step.
            # api_from_args intentionally retains its existing environment carrier.
            receipt["inventory_started"] = True
            inventory = execute(args, api_class=ReadOnlyIONOSAPI)
            receipt["inventory_completed"] = True
            inventory_pin = sha(wire(inventory))
            args.operation, args.output = "provider-classify", None
            args.provider_inventory, args.provider_inventory_sha256 = inventory_path, inventory_pin
            receipt["classification_started"] = True
            classification = execute(args)
            receipt["classification_completed"] = True
            observed = pinned(inventory_path, inventory_pin)
            if (observed != inventory or classification["inventory_sha256"] != inventory_pin
                    or classify(observed) != classification["first_boundary"]
                    or any(read.get("method") != "GET" for read in observed["reads"])):
                raise ValueError("HOLD_IONOS_PRIVATE_READBACK_MISMATCH")
            receipt.update(state=classification["state"], first_boundary=classification["first_boundary"],
                    inventory_sha256=inventory_pin, fresh_private_readback_verified=True,
                    classification={key: classification[key] for key in ("state", "first_boundary", "inventory_sha256", "resources_returned")},
                    inventory_metadata={key + "_count": len(observed[key]) for key in ("resources", "datacenters", "regions", "sizes", "images", "reads")},
                    contract_response_sha256=observed["account"]["contract_response_sha256"])
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        code = str(exc)
        preflight_errors = {"HOLD_IONOS_EXACT_SOURCE_SUBJECT_REQUIRED", "HOLD_IONOS_READONLY_BINDING_UNAVAILABLE",
                            "HOLD_IONOS_PROVIDER_BINDING_PIN_MISMATCH", "HOLD_IONOS_PROVIDER_PRODUCT_BINDING_REQUIRED",
                            "HOLD_IONOS_CONTRACT_PRINCIPAL_BINDING_REQUIRED",
                            "HOLD_IONOS_PRIVATE_READBACK_MISMATCH"}
        receipt["first_boundary"] = code if code in safe_errors | preflight_errors else "HOLD_IONOS_READONLY_EXECUTION_FAILED"
        if isinstance(exc, ProviderError): receipt["http_status"] = exc.status
    receipt["completed_at"] = timestamp()
    host.synced_private_file(receipt_path, wire(receipt)); host.sync_directory(directory)
    if decode(receipt_path.read_bytes()) != receipt:
        raise ValueError("HOLD_IONOS_METADATA_RECEIPT_READBACK_MISMATCH")
    return receipt
    raise ValueError("SUPPORTED_PROVIDER_OPERATION_REQUIRED")
