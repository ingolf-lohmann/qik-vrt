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
        if set(s) != {"schema", "provider", "organization_id", "workspace_id", "subscription", "observation",
                      "credits", "limits", "pricing", "allow_purchased", "billing_mode", "auto_reload",
                      "warning_remaining_percent", "expiry_warning_seconds"} or s["schema"] != "qikvrt_personal_budget_v1":
            raise CapabilityBlock("BUDGET_SNAPSHOT_SCHEMA_INVALID")
        provider = s["provider"]
        if provider not in {"openai", "claude"}:
            raise CapabilityBlock("BUDGET_PROVIDER_INVALID")
        identifier(s["organization_id"]); identifier(s["workspace_id"])
        if s["billing_mode"] != "prepaid" or s["auto_reload"] is not False or type(s["allow_purchased"]) is not bool:
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
            if credit["id"] in ids or credit["kind"] not in {"subscription", "purchased"}:
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
        if not isinstance(p, dict) or set(p) != {"model", "source_sha256", "valid_until", "input_token_ceiling", "max_output_tokens",
                      "input_micro_usd_per_million", "output_micro_usd_per_million", "max_request_micro_usd"}:
            raise CapabilityBlock("BOUNDED_PRICING_REQUIRED")
        identifier(p["model"])
        if not isinstance(p["source_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", p["source_sha256"]):
            raise CapabilityBlock("PRICE_EVIDENCE_REQUIRED")
        for key in set(p) - {"model", "source_sha256"}:
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
                       (c["kind"] == "subscription" or a["snapshot"]["allow_purchased"])],
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
            amount = (p["input_token_ceiling"] * p["input_micro_usd_per_million"] +
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
            known = isinstance(usage, dict) and set(usage) == {"input_tokens", "output_tokens"}
            if known:
                for value in usage.values():
                    integer(value)
                actual = (usage["input_tokens"] * p["input_micro_usd_per_million"] +
                          usage["output_tokens"] * p["output_micro_usd_per_million"] + 999999) // 1000000
                if usage["input_tokens"] > p["input_token_ceiling"] or usage["output_tokens"] > p["max_output_tokens"] or actual > op["reserved_micro_usd"]:
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
                           if c["kind"] == "subscription" or s["allow_purchased"])
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
                    "balance_evidence": "PRIVATE_OPERATOR_CONFIRMED_SNAPSHOT_MINUS_LOCAL_RESERVATIONS",
                    "provider_live_balance_verified": False, "auto_purchase": False, "auto_reload": False}
