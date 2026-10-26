# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Private, fail-closed budget ledger. No entitlement inference or payment API.

Amounts are integer micro-USD. A snapshot is an operator-confirmed observation,
not a provider balance query. BEGIN IMMEDIATE serializes independent connections.
Unknown/ambiguous usage retains the entire reservation until reconciliation.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from contextlib import contextmanager


class CapabilityBlock(ValueError):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def integer(value, *, positive=False):
    if type(value) is not int or not (1 if positive else 0) <= value <= 10**15:
        raise CapabilityBlock("BUDGET_INTEGER_REQUIRED")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise CapabilityBlock("BUDGET_IDENTIFIER_REQUIRED")
    return value


def evidence(value, subject_sha256, kind, now):
    if (not isinstance(value, dict) or
        set(value) != {"kind", "subject_sha256", "source_sha256", "observed_at", "valid_until"} or
        value["kind"] != kind or value["subject_sha256"] != subject_sha256 or
        not isinstance(value["source_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["source_sha256"])):
        raise CapabilityBlock("ENTITLEMENT_EVIDENCE_UNBOUND")
    integer(value["observed_at"]); integer(value["valid_until"])
    if not value["observed_at"] <= now < value["valid_until"]:
        raise CapabilityBlock("ENTITLEMENT_EVIDENCE_STALE_OR_FUTURE")


def check_entitlement(grant, *, provider, organization_id, workspace_id, principal_id, service_id, now):
    """Validate operator-confirmed documentary grants, never infer vendor rights.

    Catalog and each entitlement have separate exact-subject evidence. This
    checks a private operator record; it is not a vendor verification API.
    """
    if (not isinstance(grant, dict) or set(grant) != {"schema", "subject", "offer", "rights", "activation"} or
        grant["schema"] != "qikvrt_consumption_grant_v1"):
        raise CapabilityBlock("ENTITLEMENT_GRANT_REQUIRED")
    s = grant["subject"]
    if not isinstance(s, dict) or set(s) != {"provider", "organization_id", "workspace_id", "principal_id", "product_id", "sku_id", "service_id", "region", "channel"}:
        raise CapabilityBlock("ENTITLEMENT_SUBJECT_INVALID")
    for key, value in s.items():
        if key == "principal_id":
            if not isinstance(value, str) or not 1 <= len(value) <= 255 or not value.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in value):
                raise CapabilityBlock("ENTITLEMENT_PRINCIPAL_INVALID")
        else:
            identifier(value)
    if not re.fullmatch(r"[A-Z]{2}", s["region"]):
        raise CapabilityBlock("ENTITLEMENT_REGION_UNKNOWN")
    expected = {"provider": provider, "organization_id": organization_id, "workspace_id": workspace_id,
                "principal_id": principal_id, "service_id": service_id}
    if any(s[k] != v for k, v in expected.items()):
        raise CapabilityBlock("ENTITLEMENT_ACCOUNT_PRINCIPAL_OR_SERVICE_MISMATCH")
    bound = hashlib.sha256(encoded(s).encode()).hexdigest()
    offer = grant["offer"]
    if (not isinstance(offer, dict) or set(offer) != {"provider", "product_id", "sku_id", "services", "regions", "channels",
            "effective_from", "effective_until", "requires_seat", "requires_base_subscription", "default_billing_regions", "evidence"} or
        any(offer[k] != s[k] for k in ("provider", "product_id", "sku_id"))):
        raise CapabilityBlock("ENTITLEMENT_PRODUCT_SKU_CATALOG_MISMATCH")
    for key in ("services", "regions", "channels", "default_billing_regions"):
        if not isinstance(offer[key], list) or len(offer[key]) > 300:
            raise CapabilityBlock("ENTITLEMENT_CATALOG_INVALID")
        for value in offer[key]:
            identifier(value)
        if len(set(offer[key])) != len(offer[key]):
            raise CapabilityBlock("ENTITLEMENT_CATALOG_INVALID")
    if service_id not in offer["services"] or s["region"] not in offer["regions"] or s["channel"] not in offer["channels"]:
        raise CapabilityBlock("ENTITLEMENT_MARKET_CHANNEL_OR_SERVICE_UNAVAILABLE")
    integer(offer["effective_from"]); integer(offer["effective_until"])
    if not offer["effective_from"] <= now < offer["effective_until"]:
        raise CapabilityBlock("ENTITLEMENT_OFFER_NOT_EFFECTIVE")
    for key in ("requires_seat", "requires_base_subscription"):
        if type(offer[key]) is not bool:
            raise CapabilityBlock("ENTITLEMENT_LICENSE_REQUIREMENTS_UNKNOWN")
    evidence(offer["evidence"], bound, "catalog", now)
    if grant["activation"] not in {"explicit", "provider_default"}:
        raise CapabilityBlock("ENTITLEMENT_ACTIVATION_UNKNOWN")
    if grant["activation"] == "provider_default" and s["region"] not in offer["default_billing_regions"]:
        raise CapabilityBlock("ENTITLEMENT_DEFAULT_BILLING_NOT_AVAILABLE_IN_REGION")
    required = {"provider", "service", "consumption"}
    if offer["requires_seat"]:
        required.add("seat")
    if offer["requires_base_subscription"]:
        required.add("base_subscription")
    rights = grant["rights"]
    if not isinstance(rights, dict) or set(rights) - {"provider", "seat", "service", "consumption", "base_subscription"} or not required <= set(rights):
        raise CapabilityBlock("ENTITLEMENT_INDEPENDENT_RIGHTS_REQUIRED")
    for name in required:
        right = rights[name]
        right_keys = {"authorized", "evidence", "budget_sha256"} if name == "consumption" else {"authorized", "evidence"}
        if not isinstance(right, dict) or set(right) != right_keys or right["authorized"] is not True:
            raise CapabilityBlock("ENTITLEMENT_" + name.upper() + "_NOT_AUTHORIZED")
        if name == "consumption" and (not isinstance(right["budget_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", right["budget_sha256"])):
            raise CapabilityBlock("ENTITLEMENT_BUDGET_DECISION_DIGEST_REQUIRED")
        evidence(right["evidence"], bound, name, now)
    return {"state": "AUTHORIZED_FROM_OPERATOR_RECORD", "grant_sha256": hashlib.sha256(encoded(grant).encode()).hexdigest(),
            "vendor_live_entitlement_verified": False, "currency": "USD"}


class ConsumptionGuard:
    """Compose independent entitlement admission with the original budget ledger.

    Configuration is supplied by the existing protected operator store, never
    installed by an HTTP client, a plan name, SSO or a market announcement.
    """
    def __init__(self, ledger, config, *, provider, principal_id, service_id):
        if not isinstance(config, dict) or set(config) != {"schema", "grant", "budget"} or config["schema"] != "qikvrt_consumption_config_v1":
            raise CapabilityBlock("PROTECTED_CONSUMPTION_CONFIG_REQUIRED")
        self.config = json.loads(encoded(config))
        self.ledger, self.provider = ledger, provider
        self.principal_id, self.service_id = principal_id, service_id
        budget = self.config["budget"]
        if not isinstance(budget, dict) or budget.get("provider") != provider or budget.get("pricing", {}).get("model") != service_id:
            raise CapabilityBlock("ENTITLEMENT_BUDGET_PROVIDER_OR_SERVICE_MISMATCH")
        self.config_sha256 = hashlib.sha256(encoded(self.config).encode()).hexdigest()
        # Validate the grant before any initial budget persistence. On restart,
        # stale metadata remains readable but can never admit another request.
        self._validate_at = budget.get("observation", {}).get("confirmed_at")
        if type(self._validate_at) is not int:
            raise CapabilityBlock("BUDGET_OBSERVATION_INVALID")
        self.check(now=self._validate_at)
        if self.config["grant"]["rights"]["consumption"]["budget_sha256"] != hashlib.sha256(encoded(budget).encode()).hexdigest():
            raise CapabilityBlock("ENTITLEMENT_COST_LIMIT_DECISION_UNBOUND")
        ledger.install(budget)

    def check(self, *, now=None):
        budget = self.config["budget"]
        return check_entitlement(self.config["grant"], provider=self.provider,
            organization_id=budget["organization_id"], workspace_id=budget["workspace_id"],
            principal_id=self.principal_id, service_id=self.service_id,
            now=self.ledger.clock() if now is None else now)

    def reserve(self, request_id, fingerprint):
        bound = hashlib.sha256(encoded({"request": fingerprint, "config_sha256": self.config_sha256}).encode()).hexdigest()
        # A cached completed result is a read, never another paid operation.
        old = self.ledger.request(request_id, bound, self.provider)
        if old:
            return old
        self.check()
        self.check(now=self.ledger.clock() + 185)
        return self.ledger.reserve(self.provider, self.service_id, request_id, bound)

    def before_dispatch(self, reservation):
        self.check()
        self.check(now=self.ledger.clock() + 95)
        self.ledger.before_dispatch(self.provider, reservation)

    def status(self):
        try:
            result = self.check()
            budget = self.ledger.status(self.provider)
            return dict(result, state="BLOCK" if budget["state"] == "BLOCK" else result["state"],
                        budget=budget, config_sha256=self.config_sha256)
        except (CapabilityBlock, KeyError, TypeError, ValueError):
            return {"state": "BLOCK", "reason": "CONSUMPTION_EVIDENCE_MISSING_STALE_OR_UNBOUND",
                    "config_sha256": self.config_sha256, "vendor_live_entitlement_verified": False}


class BudgetLedger:
    def __init__(self, db: sqlite3.Connection, *, lock=None, clock=time.time):
        self.db, self.lock, self.clock = db, lock or threading.RLock(), clock
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS personal_budgets (provider TEXT PRIMARY KEY, body TEXT NOT NULL)")
            self.db.execute("CREATE TABLE IF NOT EXISTS personal_requests (id TEXT PRIMARY KEY, provider TEXT NOT NULL, body TEXT NOT NULL)")

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    def _account(self, provider):
        row = self.db.execute("SELECT body FROM personal_budgets WHERE provider=?", (provider,)).fetchone()
        if not row:
            raise CapabilityBlock("BUDGET_UNKNOWN")
        return json.loads(row[0])

    def _write(self, provider, account):
        self.db.execute("INSERT OR REPLACE INTO personal_budgets VALUES (?,?)", (provider, encoded(account)))

    def install(self, snapshot):
        """Import a private confirmed snapshot, at a quiescent ledger revision.

        Reimporting identical bytes is a NOOP. A new observation must postdate all
        local requests and name the current revision; a billing rollover never
        creates credits. Pending reservations prohibit replacement altogether.
        """
        s = json.loads(encoded(snapshot))
        if not isinstance(s, dict):
            raise CapabilityBlock("BUDGET_SNAPSHOT_SCHEMA_INVALID")
        # An already installed file may be expired on restart. Keep all readback
        # available; reserve() still blocks it. Identical bytes never refill it.
        with self.lock:
            row = self.db.execute("SELECT body FROM personal_budgets WHERE provider=?", (s.get("provider"),)).fetchone()
            if row and json.loads(row[0])["snapshot_sha256"] == hashlib.sha256(encoded(s).encode()).hexdigest():
                return
        version = s.get("schema")
        keys = {"schema", "provider", "organization_id", "workspace_id", "subscription", "observation",
                      "credits", "limits", "pricing", "allow_purchased", "billing_mode", "auto_reload",
                      "warning_remaining_percent", "expiry_warning_seconds"}
        if version == "qikvrt_personal_budget_v2":
            keys.add("currency")
        if set(s) != keys or version not in {"qikvrt_personal_budget_v1", "qikvrt_personal_budget_v2"}:
            raise CapabilityBlock("BUDGET_SNAPSHOT_SCHEMA_INVALID")
        if version == "qikvrt_personal_budget_v2" and s["currency"] != "USD":
            raise CapabilityBlock("BUDGET_CURRENCY_UNSUPPORTED")
        provider = s["provider"]
        if provider not in {"openai", "claude", "gemini", "microsoft_copilot"}:
            raise CapabilityBlock("BUDGET_PROVIDER_INVALID")
        if provider == "microsoft_copilot" and version != "qikvrt_personal_budget_v2":
            raise CapabilityBlock("EXPLICIT_CURRENCY_AND_UNIT_QUOTE_REQUIRED")
        identifier(s["organization_id"]); identifier(s["workspace_id"])
        bounded_usage = version == "qikvrt_personal_budget_v2" and s["billing_mode"] == "bounded_usage"
        if (s["billing_mode"] != "prepaid" and not bounded_usage) or s["auto_reload"] is not False or type(s["allow_purchased"]) is not bool:
            raise CapabilityBlock("PREPAID_WITHOUT_AUTO_RELOAD_REQUIRED")
        subscription = s["subscription"]
        if not isinstance(subscription, dict) or set(subscription) != {"plan", "status", "linked_organization_id"}:
            raise CapabilityBlock("SUBSCRIPTION_METADATA_INVALID")
        # Metadata does not generate a single unit of spending authority.
        for v in subscription.values():
            if v is not None and (not isinstance(v, str) or len(v) > 160):
                raise CapabilityBlock("SUBSCRIPTION_METADATA_INVALID")
        obs = s["observation"]
        if not isinstance(obs, dict) or set(obs) != {"id", "source_sha256", "confirmed_at", "valid_until", "ledger_revision"}:
            raise CapabilityBlock("BUDGET_OBSERVATION_INVALID")
        identifier(obs["id"])
        if not isinstance(obs["source_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", obs["source_sha256"]):
            raise CapabilityBlock("BUDGET_OBSERVATION_DIGEST_REQUIRED")
        for key in ("confirmed_at", "valid_until", "ledger_revision"):
            integer(obs[key])
        now = self.clock()
        if not obs["confirmed_at"] <= now < obs["valid_until"]:
            raise CapabilityBlock("BUDGET_OBSERVATION_STALE_OR_FUTURE")
        if not isinstance(s["credits"], list) or len(s["credits"]) > 100:
            raise CapabilityBlock("CREDIT_POOLS_INVALID")
        ids = set()
        for credit in s["credits"]:
            if not isinstance(credit, dict) or set(credit) != {"id", "kind", "remaining_micro_usd", "expires_at", "cycle_id"}:
                raise CapabilityBlock("CREDIT_POOL_INVALID")
            identifier(credit["id"])
            kinds = {"authorized_usage"} if bounded_usage else {"subscription", "purchased"}
            if credit["id"] in ids or credit["kind"] not in kinds:
                raise CapabilityBlock("CREDIT_POOL_INVALID")
            ids.add(credit["id"])
            if credit["remaining_micro_usd"] is not None:
                integer(credit["remaining_micro_usd"])
            if credit["expires_at"] is not None:
                integer(credit["expires_at"], positive=True)
            if credit["kind"] == "subscription":
                identifier(credit["cycle_id"])
                if credit["expires_at"] is None or subscription["linked_organization_id"] != s["organization_id"]:
                    raise CapabilityBlock("SUBSCRIPTION_CREDIT_EXPIRY_AND_LINK_REQUIRED")
        if not isinstance(s["limits"], list) or not all(isinstance(v, dict) for v in s["limits"]) or {v.get("id") for v in s["limits"]} != {"local", "organization", "workspace"} or len(s["limits"]) != 3:
            raise CapabilityBlock("INDEPENDENT_SPEND_LIMITS_REQUIRED")
        for limit in s["limits"]:
            if set(limit) != {"id", "period_start", "period_end", "remaining_micro_usd"}:
                raise CapabilityBlock("SPEND_LIMIT_INVALID")
            integer(limit["period_start"]); integer(limit["period_end"])
            if limit["period_start"] >= limit["period_end"]:
                raise CapabilityBlock("SPEND_LIMIT_PERIOD_INVALID")
            if limit["remaining_micro_usd"] is not None:
                integer(limit["remaining_micro_usd"])
        p = s["pricing"]
        unit_quote = version == "qikvrt_personal_budget_v2" and isinstance(p, dict) and p.get("kind") == "units"
        if unit_quote:
            if set(p) != {"kind", "model", "source_sha256", "valid_until", "unit", "max_units", "unit_micro_usd", "max_request_micro_usd"}:
                raise CapabilityBlock("BOUNDED_UNIT_QUOTE_REQUIRED")
            identifier(p["unit"])
        elif not isinstance(p, dict) or set(p) != {"model", "source_sha256", "valid_until", "input_token_ceiling", "max_output_tokens",
                      "input_micro_usd_per_million", "output_micro_usd_per_million", "max_request_micro_usd"}:
            raise CapabilityBlock("BOUNDED_PRICING_REQUIRED")
        identifier(p["model"])
        if not isinstance(p["source_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", p["source_sha256"]):
            raise CapabilityBlock("PRICE_EVIDENCE_REQUIRED")
        for key in set(p) - {"model", "source_sha256", "kind", "unit"}:
            integer(p[key], positive=True)
        if not isinstance(s["warning_remaining_percent"], list) or not s["warning_remaining_percent"] or any(type(x) is not int or not 0 < x < 100 for x in s["warning_remaining_percent"]):
            raise CapabilityBlock("BUDGET_WARNING_THRESHOLDS_INVALID")
        integer(s["expiry_warning_seconds"])
        sha = hashlib.sha256(encoded(s).encode()).hexdigest()
        with self.transaction():
            row = self.db.execute("SELECT body FROM personal_budgets WHERE provider=?", (provider,)).fetchone()
            old = json.loads(row[0]) if row else None
            if old and old["snapshot_sha256"] == sha:
                return  # Never refill a consumed snapshot on restart.
            if old:
                pending = any(json.loads(r[0])["state"] != "COMPLETED" for r in self.db.execute(
                    "SELECT body FROM personal_requests WHERE provider=?", (provider,)))
                if pending or old.get("frozen"):
                    raise CapabilityBlock("UNRESOLVED_RESERVATIONS_REQUIRE_RECONCILIATION")
                if (obs["ledger_revision"] != old["revision"] or obs["id"] == old["snapshot"]["observation"]["id"] or
                    obs["confirmed_at"] <= old["snapshot"]["observation"]["confirmed_at"] or
                    obs["confirmed_at"] < old["last_event"]):
                    raise CapabilityBlock("BUDGET_RECONCILIATION_REVISION_OR_TIME_MISMATCH")
                if (s["organization_id"], s["workspace_id"]) != (old["snapshot"]["organization_id"], old["snapshot"]["workspace_id"]):
                    raise CapabilityBlock("BUDGET_ACCOUNT_CHANGE_REQUIRES_NEW_PRIVATE_STORE")
            elif obs["ledger_revision"] != 0:
                raise CapabilityBlock("BUDGET_INITIAL_REVISION_MUST_BE_ZERO")
            self._write(provider, {"snapshot": s, "snapshot_sha256": sha, "revision": obs["ledger_revision"],
                                   "credits": s["credits"], "limits": s["limits"], "last_event": now, "frozen": False})

    def _eligible(self, a, now):
        return sorted([c for c in a["credits"] if c["remaining_micro_usd"] is not None and
                       c["expires_at"] is not None and now < c["expires_at"] and
                       (c["kind"] in {"subscription", "authorized_usage"} or a["snapshot"]["allow_purchased"])],
                      key=lambda c: (c["kind"] != "subscription", c["expires_at"] or 10**15, c["id"]))

    def _check(self, a, model, now):
        s = a["snapshot"]
        if a["frozen"]:
            raise CapabilityBlock("BUDGET_FROZEN_RECONCILIATION_REQUIRED")
        if now < a["last_event"] or not s["observation"]["confirmed_at"] <= now < s["observation"]["valid_until"]:
            raise CapabilityBlock("BUDGET_STALE_OR_CLOCK_ROLLBACK")
        p = s["pricing"]
        if p["model"] != model or now >= p["valid_until"]:
            raise CapabilityBlock("MODEL_PRICE_BINDING_MISSING_OR_EXPIRED")
        for limit in a["limits"]:
            if limit["remaining_micro_usd"] is None or not limit["period_start"] <= now < limit["period_end"]:
                raise CapabilityBlock("SPEND_LIMIT_UNKNOWN_OR_PERIOD_CHANGED")
        if not self._eligible(a, now):
            raise CapabilityBlock("CREDIT_BALANCE_UNKNOWN_OR_EXPIRED")

    def request(self, request_id, fingerprint, provider):
        identifier(request_id)
        row = self.db.execute("SELECT provider,body FROM personal_requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            return None
        op = json.loads(row[1])
        if row[0] != provider or op["fingerprint"] != fingerprint:
            raise CapabilityBlock("REQUEST_ID_CONFLICT_OR_PROVIDER_SWITCH_DENIED")
        if op["state"] != "COMPLETED":
            raise CapabilityBlock("PRIOR_PROVIDER_RESULT_UNRESOLVED_READBACK_REQUIRED_NO_RETRY")
        return op

    def reserve(self, provider, model, request_id, fingerprint):
        """Reserve the configured model's full input ceiling + bounded output.

        Never treat token-count estimates as a spending upper bound. The private
        price contract must cover all applicable tiers for text-only requests.
        """
        with self.transaction():
            existing = self.request(request_id, fingerprint, provider)
            if existing:
                return existing
            a = self._account(provider); now = self.clock(); self._check(a, model, now)
            p = a["snapshot"]["pricing"]
            amount = p["max_units"] * p["unit_micro_usd"] if p.get("kind") == "units" else (p["input_token_ceiling"] * p["input_micro_usd_per_million"] +
                      p["max_output_tokens"] * p["output_micro_usd_per_million"] + 999999) // 1000000
            credits = self._eligible(a, now)
            if amount > min([p["max_request_micro_usd"], sum(c["remaining_micro_usd"] for c in credits)] +
                            [v["remaining_micro_usd"] for v in a["limits"]]):
                raise CapabilityBlock("BUDGET_EXHAUSTED_OR_RESERVATION_EXCEEDS_LIMIT")
            # Do not begin a request whose time allowance crosses a known boundary.
            deadline = now + 185  # two bounded HTTP operations plus a margin
            if deadline >= min(s for s in [a["snapshot"]["observation"]["valid_until"], p["valid_until"],
                                          *[v["period_end"] for v in a["limits"]]]):
                raise CapabilityBlock("BUDGET_BOUNDARY_TOO_CLOSE")
            remaining, allocations = amount, []
            for c in credits:
                if c["expires_at"] is not None and deadline >= c["expires_at"]:
                    continue
                take = min(remaining, c["remaining_micro_usd"])
                if take:
                    allocations.append({"id": c["id"], "amount": take})
                    c["remaining_micro_usd"] -= take; remaining -= take
            if remaining:
                raise CapabilityBlock("CREDIT_EXPIRY_TOO_CLOSE")
            for limit in a["limits"]:
                limit["remaining_micro_usd"] -= amount
            a["revision"] += 1; a["last_event"] = now
            op = {"state": "RESERVED", "fingerprint": fingerprint, "reserved_micro_usd": amount,
                  "allocations": allocations, "pricing": p, "snapshot_sha256": a["snapshot_sha256"],
                  "organization_id": a["snapshot"]["organization_id"], "workspace_id": a["snapshot"]["workspace_id"],
                  "created_at": now}
            self._write(provider, a)
            self.db.execute("INSERT INTO personal_requests VALUES (?,?,?)", (request_id, provider, encoded(op)))
            return op

    def before_dispatch(self, provider, reservation):
        """Recheck after a slow preflight, immediately before the paid request."""
        with self.lock:
            a = self._account(provider); now = self.clock()
            self._check(a, reservation["pricing"]["model"], now)
            if a["snapshot_sha256"] != reservation["snapshot_sha256"]:
                raise CapabilityBlock("RESERVATION_SNAPSHOT_CHANGED_NO_RETRY")
            grant_ids = {v["id"] for v in reservation["allocations"]}
            boundaries = [a["snapshot"]["observation"]["valid_until"], reservation["pricing"]["valid_until"],
                          *[v["period_end"] for v in a["limits"]],
                          *[v["expires_at"] for v in a["credits"] if v["id"] in grant_ids]]
            if now + 95 >= min(boundaries):
                raise CapabilityBlock("BUDGET_BOUNDARY_BEFORE_DISPATCH_NO_RETRY")

    def finish(self, provider, request_id, usage, result):
        """Settle only recognized usage. Unknown billing retains the maximum hold."""
        problem = None
        with self.transaction():
            row = self.db.execute("SELECT provider,body FROM personal_requests WHERE id=?", (request_id,)).fetchone()
            if not row or row[0] != provider:
                raise CapabilityBlock("RESERVATION_NOT_FOUND")
            op = json.loads(row[1]); a = self._account(provider)
            if op["state"] == "COMPLETED":
                return
            p = op["pricing"]
            actual = op["reserved_micro_usd"]
            units = p.get("kind") == "units"
            known = isinstance(usage, dict) and set(usage) == ({"units"} if units else {"input_tokens", "output_tokens"})
            if known and any(type(value) is not int or not 0 <= value <= 10**15 for value in usage.values()):
                known = False
            if known:
                for value in usage.values():
                    integer(value)
                actual = usage["units"] * p["unit_micro_usd"] if units else (usage["input_tokens"] * p["input_micro_usd_per_million"] +
                          usage["output_tokens"] * p["output_micro_usd_per_million"] + 999999) // 1000000
                over_bound = usage["units"] > p["max_units"] if units else (usage["input_tokens"] > p["input_token_ceiling"] or usage["output_tokens"] > p["max_output_tokens"])
                if over_bound or actual > op["reserved_micro_usd"]:
                    a["frozen"] = True; problem = "PROVIDER_USAGE_EXCEEDS_PRICE_BOUND_RECONCILIATION_REQUIRED"
            if not known:
                a["frozen"] = True; problem = "PROVIDER_USAGE_UNKNOWN_RECONCILIATION_REQUIRED"
            if problem:
                op.update(state="UNRESOLVED", reason=problem)
            else:
                # Refund purchased/latest-expiring allocations first, preserving promo-first use.
                refund = op["reserved_micro_usd"] - actual
                for allocation in reversed(op["allocations"]):
                    take = min(refund, allocation["amount"])
                    next(c for c in a["credits"] if c["id"] == allocation["id"])["remaining_micro_usd"] += take
                    refund -= take
                for limit in a["limits"]:
                    limit["remaining_micro_usd"] += op["reserved_micro_usd"] - actual
                op.update(state="COMPLETED", cost_upper_bound_micro_usd=actual, result=result)
            a["revision"] += 1; a["last_event"] = self.clock()
            self._write(provider, a)
            self.db.execute("UPDATE personal_requests SET body=? WHERE id=?", (encoded(op), request_id))
        if problem:
            raise CapabilityBlock(problem)

    def status(self, provider):
        with self.lock:
            try:
                a = self._account(provider)
            except CapabilityBlock:
                return {"state": "BLOCK", "reason": "BUDGET_UNKNOWN", "provider": provider}
            now = self.clock(); s = a["snapshot"]
            available = sum(c["remaining_micro_usd"] for c in self._eligible(a, now))
            original = sum(c["remaining_micro_usd"] or 0 for c in s["credits"]
                           if c["kind"] in {"subscription", "authorized_usage"} or s["allow_purchased"])
            warnings = []
            for percent in sorted(set(s["warning_remaining_percent"]), reverse=True):
                if original and available * 100 <= original * percent:
                    warnings.append("CREDIT_REMAINING_AT_OR_BELOW_" + str(percent) + "_PERCENT")
                for limit in a["limits"]:
                    initial = next(v for v in s["limits"] if v["id"] == limit["id"])["remaining_micro_usd"]
                    if initial and limit["remaining_micro_usd"] is not None and limit["remaining_micro_usd"] * 100 <= initial * percent:
                        warnings.append(limit["id"].upper() + "_LIMIT_AT_OR_BELOW_" + str(percent) + "_PERCENT")
            if any(c["expires_at"] is not None and 0 < c["expires_at"] - now <= s["expiry_warning_seconds"] for c in a["credits"]):
                warnings.append("CREDIT_EXPIRY_APPROACHING")
            try:
                self._check(a, s["pricing"]["model"], now)
                state, reason = ("READY", None) if available and all(v["remaining_micro_usd"] for v in a["limits"]) else ("BLOCK", "BUDGET_EXHAUSTED")
            except CapabilityBlock as exc:
                state, reason = "BLOCK", str(exc)
            return {"state": state, "reason": reason, "provider": provider, "revision": a["revision"],
                    "subscription": s["subscription"], "organization_id": s["organization_id"], "workspace_id": s["workspace_id"],
                    "credits": a["credits"], "limits": a["limits"], "observation": s["observation"],
                    "available_micro_usd": available, "warnings": warnings,
                    "billing_mode": s["billing_mode"],
                    "balance_evidence": ("PRIVATE_OPERATOR_SPEND_ALLOWANCE_MINUS_LOCAL_RESERVATIONS" if s["billing_mode"] == "bounded_usage" else
                                         "PRIVATE_OPERATOR_CONFIRMED_SNAPSHOT_MINUS_LOCAL_RESERVATIONS"),
                    "provider_live_balance_verified": False, "auto_purchase": False, "auto_reload": False}
