# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Personal input/goal transitions on the existing native CAS event carrier.

No database, executor, scheduler, network client or background loop is added.
Channel readback is an explicitly installed, trusted adapter capability; input
JSON cannot supply it or establish delivery. All data stays in the private store.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

try:
    from .qikvrt_digital_twin_schedule_events import (
        OPERATION_SCHEMA, closed, decode, identifier, integer, instant, subject,
        text, time_binding,
    )
    from .qikvrt_digital_twin_scheduling import ScheduleConflict, canonical, digest
except ImportError:
    from qikvrt_digital_twin_schedule_events import (
        OPERATION_SCHEMA, closed, decode, identifier, integer, instant, subject,
        text, time_binding,
    )
    from qikvrt_digital_twin_scheduling import ScheduleConflict, canonical, digest

SCHEMA = "qikvrt_digital_twin_personal_v1"
INPUT_SCHEMA = "qikvrt_personal_input_v1"
BASE = "/api/digital-twin/v1/personal"
REQUIREMENT_FIELDS = {
    "requirement_id", "origin_reference_and_epistemic_type",
    "repository_role_and_exact_source", "current_revision_and_supersedes",
    "purpose_and_beneficiary", "inputs_preconditions_and_authorization_scope",
    "supported_human_context_and_boundaries", "expected_observable_effect",
    "verification_method_and_independent_readback", "acceptance_predicates",
    "dependencies_and_failure_or_recovery_behavior", "privacy_security_and_rights_constraints",
    "owner_choices_and_their_resolution", "implementation_and_test_bindings",
    "actual_effect_receipt_and_acceptance_disposition", "current_quality_procedure_fingerprint",
    "next_action_or_material_retry_condition",
}


def requirement(raw):
    value = closed(raw, REQUIREMENT_FIELDS, "PERSONAL_REQUIREMENT")
    identifier(value["requirement_id"], "REQUIREMENT_ID")
    origin = closed(value["origin_reference_and_epistemic_type"], {"reference", "epistemic_type"}, "ORIGIN")
    text(origin["reference"], 4096, "ORIGIN_REFERENCE")
    if origin["epistemic_type"] not in (
        "HUMAN_DIRECTIVE", "NORMATIVE", "IMPLEMENTATION", "TEST", "DOCUMENTARY_SOURCE", "PROPOSAL"
    ):
        raise ValueError("INVALID_ORIGIN_TYPE")
    subject(value["repository_role_and_exact_source"])
    revision = closed(value["current_revision_and_supersedes"], {"revision", "supersedes"}, "REVISION")
    integer(revision["revision"], 1, 2**63 - 1, "REQUIREMENT_REVISION")
    if revision["supersedes"] is not None:
        identifier(revision["supersedes"], "SUPERSEDES_HASH")
    identifier(value["current_quality_procedure_fingerprint"], "PROCEDURE_HASH")
    text(value["purpose_and_beneficiary"], 4096, "PURPOSE")
    predicates = value["acceptance_predicates"]
    if predicates is not None:
        if not isinstance(predicates, list) or len(predicates) > 64:
            raise ValueError("INVALID_ACCEPTANCE_PREDICATES")
        for predicate in predicates:
            text(predicate, 4096, "ACCEPTANCE_PREDICATE")
    choices = value["owner_choices_and_their_resolution"]
    if not isinstance(choices, list) or len(choices) > 64:
        raise ValueError("INVALID_OWNER_CHOICES")
    seen = set()
    for choice in choices:
        closed(choice, {"decision_id", "question", "necessary", "resolution"}, "OWNER_CHOICE")
        identifier(choice["decision_id"], "DECISION_ID")
        text(choice["question"], 4096, "OWNER_QUESTION")
        if type(choice["necessary"]) is not bool:
            raise ValueError("BOOLEAN_NECESSARY_REQUIRED")
        if choice["resolution"] is not None:
            text(choice["resolution"], 4096, "OWNER_RESOLUTION")
        if choice["decision_id"] in seen:
            raise ValueError("DUPLICATE_DECISION_ID")
        seen.add(choice["decision_id"])
    # The native decoder supplies the shared size/depth/noncanonical-type bounds.
    return decode(canonical(value).encode())


def context(raw):
    closed(raw, {"channel_id", "language", "modality"}, "HUMAN_CONTEXT")
    for key in raw:
        text(raw[key], 256, key.upper())
    return dict(raw)


def priority(raw):
    closed(raw, {"main_goal", "continuing_goal", "deadline_utc", "impact", "reason"}, "PRIORITY")
    for key in ("main_goal", "continuing_goal"):
        if type(raw[key]) is not bool:
            raise ValueError("BOOLEAN_PRIORITY_FLAG_REQUIRED")
    integer(raw["impact"], 0, 5, "IMPACT")
    text(raw["reason"], 4096, "PRIORITY_REASON")
    if raw["deadline_utc"] is not None:
        instant(raw["deadline_utc"])
    return dict(raw)


class PersonalAdapter:
    """Semantic adapter, sharing a ScheduleEventStore instance and its ledger."""

    def __init__(self, store, *, channels=None, channel_readback=None):
        self.store = store
        self.channels = {} if channels is None else decode(canonical(channels).encode())
        if not isinstance(self.channels, dict) or len(self.channels) > 64:
            raise ValueError("INVALID_PERSONAL_CHANNEL_CONFIGURATION")
        for name, configuration in self.channels.items():
            text(name, 256, "CHANNEL_ID")
            closed(configuration, {"principal", "languages", "modalities"}, "CHANNEL_CONFIGURATION")
            text(configuration["principal"], 256, "CHANNEL_PRINCIPAL")
            for field in ("languages", "modalities"):
                if not isinstance(configuration[field], list) or not 1 <= len(configuration[field]) <= 32:
                    raise ValueError("INVALID_CHANNEL_CAPABILITIES")
                for item in configuration[field]:
                    text(item, 256, "CHANNEL_CAPABILITY")
        if channel_readback is not None and not callable(channel_readback):
            raise ValueError("CALLABLE_TRUSTED_CHANNEL_READBACK_REQUIRED")
        self.channel_readback = channel_readback

    def _payload(self, event):
        if event["deleted"]:
            raise ScheduleConflict("PERSONAL_GOAL_TOMBSTONED")
        payload = event["value"]["payload"]
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
            raise ValueError("NOT_A_PERSONAL_GOAL")
        if payload.get("principal") != self.store.principal:
            raise ScheduleConflict("EXACT_PERSONAL_PRINCIPAL_REQUIRED")
        if payload["requirement"]["requirement_id"] != event["event_id"]:
            raise ScheduleConflict("PERSONAL_REQUIREMENT_ID_MISMATCH")
        return payload

    def _coverage(self, goal):
        ctx = goal["context"]
        compatible = sorted(name for name, c in self.channels.items()
                            if c["principal"] == self.store.principal
                            and ctx["language"] in c["languages"] and ctx["modality"] in c["modalities"])
        return {"supported": ctx["channel_id"] in compatible,
                "authorized_alternative_channel": next((name for name in compatible if name != ctx["channel_id"]), None)}

    def _readiness(self, goal):
        req = goal["requirement"]
        missing = sorted(key for key, value in req.items() if value is None or value == [] or value == "")
        # An explicitly empty list of Owner decisions means no necessary question.
        missing = [key for key in missing if key != "owner_choices_and_their_resolution"]
        questions = [c for c in req["owner_choices_and_their_resolution"] if c["necessary"] and c["resolution"] is None]
        if goal["state"] == "CANCELLED":
            state = "CANCELLED"
        elif req["repository_role_and_exact_source"] != self.store.subject:
            state = "HOLD_EXACT_SOURCE_OR_ROLE_UNVERIFIED"
        elif not self._coverage(goal)["supported"]:
            state = "HOLD_UNSUPPORTED_HUMAN_CONTEXT"
        elif goal["procedure_sha256"] != req["current_quality_procedure_fingerprint"]:
            state = "OPEN_REVALIDATION_REQUIRED"
        elif goal["blocker"]:
            state = "OPEN_BLOCKED"
        elif missing or questions or req["origin_reference_and_epistemic_type"]["epistemic_type"] == "PROPOSAL":
            state = "OPEN"
        else:
            state = "READY_FOR_IMPLEMENTATION"
        return {"state": state, "missing_fields": missing, "necessary_owner_choices": questions,
                "routine_refinement_first": True, "readiness_is_authorization": False}

    def _project(self, event):
        goal = self._payload(event)
        same_subject = event["last_subject"] == self.store.subject
        feedback = goal["feedback"]
        delivery = feedback["delivery_state"] if feedback else "NOT_REQUIRED"
        if not same_subject and feedback:
            delivery = "INVALIDATED_EXACT_SUBJECT_CHANGED"
        return {"event": event, "readiness": self._readiness(goal), "context_coverage": self._coverage(goal),
                "delivery_state": delivery, "prepared_action_current": bool(
                    goal["prepared_action"] and goal["prepared_action"]["state"] == "PENDING_NOT_EXECUTED"
                    and goal["prepared_action"]["subject"] == self.store.subject
                    and self._readiness(goal)["state"] == "READY_FOR_IMPLEMENTATION"),
                "human_understanding_inferred": False, "global_goal_done": False, "effect_ack_done": False}

    def read(self, requirement_id=None):
        native = self.store.read(requirement_id)
        goals = []
        for event in native["events"]:
            if not event["deleted"] and isinstance(event["value"]["payload"], dict) and event["value"]["payload"].get("schema") == SCHEMA:
                goals.append(self._project(event))
            elif requirement_id is not None:
                raise ValueError("NOT_AN_ACTIVE_PERSONAL_GOAL")
        return {"schema": SCHEMA, "subject": self.store.subject, "principal": self.store.principal,
                "goals": goals, "predecessor_evidence_transfer": False, "effect_ack_done": False}

    def prioritize(self, at_utc):
        now = instant(at_utc)
        entries = []
        for projection in self.read()["goals"]:
            goal = projection["event"]["value"]["payload"]
            if goal["state"] == "CANCELLED":
                continue
            p = goal["priority"]
            urgent = p["deadline_utc"] is not None and instant(p["deadline_utc"]) <= now + timedelta(hours=24)
            entries.append({"requirement_id": goal["requirement"]["requirement_id"], "strand_id": goal["strand_id"],
                            "version": projection["event"]["version"], "urgent": urgent, "priority": p,
                            "priority_reason": ("Declared deadline within 24 hours: " if urgent else "Declared impact/main-goal order: ") + p["reason"]})
        entries.sort(key=lambda e: (not e["urgent"], e["priority"]["deadline_utc"] if e["urgent"] else "",
                                   -e["priority"]["impact"], not e["priority"]["main_goal"], e["requirement_id"]))
        return {"schema": SCHEMA, "entries": entries, "dispatch_performed": False, "effect_ack_done": False}

    def _notify(self, goal):
        ready = self._readiness(goal)
        needed = bool(goal["blocker"] or ready["necessary_owner_choices"] or ready["state"].startswith(("HOLD_", "OPEN_REVALIDATION")))
        if not needed:
            goal["feedback"] = None
            return
        fingerprint = digest({"requirement": digest(goal["requirement"]), "subject": self.store.subject,
                              "blocker": goal["blocker"], "retry": goal["retry_condition"],
                              "procedure": goal["procedure_sha256"], "context": goal["context"],
                              "coverage": self._coverage(goal), "readiness": ready})
        if goal["feedback"] and goal["feedback"]["fingerprint"] == fingerprint:
            return
        message = {"strand_id": goal["strand_id"], "requirement_id": goal["requirement"]["requirement_id"],
                   "plain_language_purpose": goal["requirement"]["purpose_and_beneficiary"],
                   "verified_state": ready["state"], "source_binding": self.store.subject,
                   "precise_remainder_or_decision": {"blocker": goal["blocker"], "choices": ready["necessary_owner_choices"], "missing_fields": ready["missing_fields"]},
                   "priority_reason": goal["priority"]["reason"], "smallest_next_action": goal["retry_condition"],
                   "reactivation_condition": goal["retry_condition"]}
        goal["feedback"] = {"feedback_id": digest({"principal": self.store.principal, "fingerprint": fingerprint}),
                            "fingerprint": fingerprint, "message": message, "message_sha256": digest(message),
                            "delivery_state": "RECEIPT_PENDING", "attempt": None, "observation": None}

    def _delivery(self, goal, data):
        closed(data, {"feedback_id", "attempt_id"}, "FEEDBACK_READBACK")
        feedback = goal["feedback"]
        if not feedback or data["feedback_id"] != feedback["feedback_id"] or not feedback["attempt"] or data["attempt_id"] != feedback["attempt"]["attempt_id"]:
            raise ScheduleConflict("EXACT_FEEDBACK_ATTEMPT_REQUIRED")
        if feedback["delivery_state"] == "DELIVERED_CHANNEL_READBACK":
            return False
        if self.channel_readback is None:
            return False
        attempt = feedback["attempt"]
        expected = {"principal": self.store.principal, "channel_id": attempt["channel_id"],
                    "attempt_id": attempt["attempt_id"], "message_sha256": feedback["message_sha256"]}
        observation = self.channel_readback(dict(expected))
        if observation is None:
            return False
        closed(observation, {*expected, "delivered", "observed_at_utc", "receipt_id"}, "TRUSTED_CHANNEL_READBACK")
        if any(observation[key] != value for key, value in expected.items()):
            raise ScheduleConflict("CHANNEL_READBACK_BINDING_MISMATCH")
        if type(observation["delivered"]) is not bool:
            raise ValueError("BOOLEAN_DELIVERED_REQUIRED")
        text(observation["receipt_id"], 256, "CHANNEL_RECEIPT_ID")
        observed = instant(observation["observed_at_utc"])
        now = datetime.now(timezone.utc)
        if observed < instant(attempt["recorded_at_utc"]) or observed > now + timedelta(seconds=30) or now - observed > timedelta(minutes=5):
            raise ScheduleConflict("FRESH_CHANNEL_READBACK_REQUIRED")
        if not observation["delivered"]:
            return False
        feedback["observation"] = observation
        feedback["delivery_state"] = "DELIVERED_CHANNEL_READBACK"
        return True

    def apply(self, raw):
        raw = decode(canonical(raw).encode())
        closed(raw, {"schema", "input_id", "requirement_id", "expected_version", "transition", "data"}, "PERSONAL_INPUT")
        if raw["schema"] != INPUT_SCHEMA:
            raise ValueError("UNSUPPORTED_PERSONAL_INPUT_SCHEMA")
        for key in ("input_id", "requirement_id"):
            identifier(raw[key], key.upper())
        integer(raw["expected_version"], 0, 2**63 - 1, "EXPECTED_VERSION")
        transition = raw["transition"]
        if transition not in ("input", "correct", "cancel", "observe", "prepare_action", "feedback_attempt", "feedback_readback", "human_feedback"):
            raise ValueError("UNSUPPORTED_PERSONAL_TRANSITION")
        input_hash = digest(raw)
        with self.store.connect() as db:
            prior = db.execute("SELECT record FROM schedule_operations WHERE id=?", (raw["input_id"],)).fetchone()
        if prior is not None:
            record = json.loads(prior[0])
            payload = record["request"]["value"]["payload"] if record["request"]["value"] else None
            if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("last_input", {}).get("sha256") != input_hash:
                raise ScheduleConflict("PERSONAL_INPUT_ID_CONTENT_COLLISION")
            result = self.store.apply(record["request"])
            return dict(result, schema=SCHEMA, state="REPLAY_HISTORICAL_ONLY")
        data = raw["data"]
        if transition == "input":
            closed(data, {"strand_id", "requirement", "priority", "context", "input"}, "PERSONAL_CREATE")
            identifier(data["strand_id"], "STRAND_ID")
            req = requirement(data["requirement"])
            if req["current_revision_and_supersedes"] != {"revision": 1, "supersedes": None}:
                raise ValueError("INITIAL_REQUIREMENT_REVISION_REQUIRED")
            goal = {"schema": SCHEMA, "principal": self.store.principal, "strand_id": data["strand_id"],
                    "requirement": req, "priority": priority(data["priority"]), "context": context(data["context"]),
                    "input": data["input"], "state": "RECEIVED", "procedure_sha256": req["current_quality_procedure_fingerprint"],
                    "blocker": None, "retry_condition": "Refine missing fields, then use the existing admitted executor.",
                    "feedback": None, "prepared_action": None, "human_feedback": []}
            value = {"title": "Personal requirement " + req["requirement_id"], "payload": goal,
                     "enabled": False, "start": time_binding("2000-01-01T00:00:00", "UTC"), "recurrence": None}
            kind = "create"
        else:
            event = self.store.read(raw["requirement_id"])["events"][0]
            if event["version"] != raw["expected_version"]:
                raise ScheduleConflict("STALE_EXACT_PERSONAL_VERSION")
            goal = decode(canonical(self._payload(event)).encode())
            if goal["state"] == "CANCELLED":
                raise ScheduleConflict("CANCELLED_GOAL_CANNOT_REACTIVATE")
            value = decode(canonical(event["value"]).encode())
            value["payload"] = goal
            kind = "update"
            if transition == "correct":
                closed(data, {"requirement", "priority", "context", "input"}, "PERSONAL_CORRECTION")
                req = requirement(data["requirement"])
                previous = goal["requirement"]
                if req["current_revision_and_supersedes"] != {"revision": previous["current_revision_and_supersedes"]["revision"] + 1, "supersedes": digest(previous)}:
                    raise ScheduleConflict("EXACT_REQUIREMENT_SUPERSESSION_REQUIRED")
                goal.update(requirement=req, priority=priority(data["priority"]), context=context(data["context"]),
                            input=data["input"], procedure_sha256=req["current_quality_procedure_fingerprint"],
                            state="RECEIVED", blocker=None, feedback=None)
            elif transition == "cancel":
                closed(data, {"reason"}, "PERSONAL_CANCELLATION")
                goal.update(state="CANCELLED", blocker=text(data["reason"], 4096, "CANCELLATION_REASON"))
                if goal["feedback"]:
                    goal["feedback"]["delivery_state"] = "INVALIDATED_CANCELLED"
            elif transition == "observe":
                closed(data, {"blocker", "retry_condition", "procedure_sha256", "context"}, "PERSONAL_OBSERVATION")
                if data["blocker"] is not None:
                    text(data["blocker"], 4096, "BLOCKER")
                goal.update(blocker=data["blocker"], retry_condition=text(data["retry_condition"], 4096, "RETRY_CONDITION"),
                            procedure_sha256=identifier(data["procedure_sha256"], "PROCEDURE_HASH"), context=context(data["context"]))
            else:
                # Changes of code subject invalidate action and delivery evidence.
                if event["last_subject"] != self.store.subject:
                    raise ScheduleConflict("CURRENT_SUBJECT_REOBSERVATION_REQUIRED")
                if transition == "prepare_action":
                    closed(data, {"action_id"}, "PREPARE_PERSONAL_ACTION")
                    if self._readiness(goal)["state"] != "READY_FOR_IMPLEMENTATION" or (goal["prepared_action"] and goal["prepared_action"]["state"] == "PENDING_NOT_EXECUTED"):
                        raise ScheduleConflict("CURRENT_READY_UNPREPARED_GOAL_REQUIRED")
                    goal["prepared_action"] = {"action_id": identifier(data["action_id"], "ACTION_ID"),
                                               "subject": self.store.subject, "requirement_sha256": digest(goal["requirement"]),
                                               "procedure_sha256": goal["procedure_sha256"], "state": "PENDING_NOT_EXECUTED"}
                elif transition == "feedback_attempt":
                    closed(data, {"feedback_id", "attempt_id", "channel_id", "transport_ack"}, "FEEDBACK_ATTEMPT")
                    feedback = goal["feedback"]
                    if not feedback or feedback["feedback_id"] != data["feedback_id"] or feedback["attempt"] is not None:
                        raise ScheduleConflict("UNATTEMPTED_CURRENT_FEEDBACK_REQUIRED")
                    ctx = dict(goal["context"], channel_id=data["channel_id"])
                    probe = dict(goal, context=context(ctx))
                    if not self._coverage(probe)["supported"] or type(data["transport_ack"]) is not bool:
                        raise ValueError("AUTHORIZED_COMPATIBLE_CHANNEL_AND_BOOLEAN_ACK_REQUIRED")
                    feedback["attempt"] = {"attempt_id": identifier(data["attempt_id"], "ATTEMPT_ID"),
                                           "channel_id": data["channel_id"], "transport_ack": data["transport_ack"],
                                           "recorded_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")}
                    feedback["delivery_state"] = "DELIVERY_PENDING"
                elif transition == "feedback_readback":
                    self._delivery(goal, data)
                elif transition == "human_feedback":
                    closed(data, {"feedback_id", "response", "scope_acceptance"}, "HUMAN_FEEDBACK")
                    if not goal["feedback"] or data["feedback_id"] != goal["feedback"]["feedback_id"]:
                        raise ScheduleConflict("CURRENT_FEEDBACK_REQUIRED")
                    if data["scope_acceptance"] not in ("NONE", "ACCEPTED", "REJECTED"):
                        raise ValueError("INVALID_SCOPE_ACCEPTANCE")
                    text(data["response"], 4096, "HUMAN_RESPONSE")
                    if len(goal["human_feedback"]) >= 64:
                        raise ValueError("HUMAN_FEEDBACK_CAPACITY_EXCEEDED")
                    goal["human_feedback"].append(dict(data, input_id=raw["input_id"]))
            if transition in ("correct", "cancel", "observe"):
                action = goal["prepared_action"]
                if action and (transition != "observe" or action["subject"] != self.store.subject
                               or self._readiness(goal)["state"] != "READY_FOR_IMPLEMENTATION"):
                    action["state"] = "INVALIDATED"
                if event["last_subject"] != self.store.subject:
                    goal["feedback"] = None
        if goal["requirement"]["requirement_id"] != raw["requirement_id"]:
            raise ScheduleConflict("EXACT_REQUIREMENT_ID_REQUIRED")
        if transition in ("input", "correct", "observe"):
            self._notify(goal)
        if transition != "input" and digest(value) == digest(event["value"]):
            current = self.store.read(raw["requirement_id"])
            if digest(current["events"][0]) != digest(event):
                raise ScheduleConflict("NOOP_READBACK_CHANGED")
            return {"schema": SCHEMA, "state": "NOOP_UNCHANGED", "readback": current,
                    "notification_created": False, "effect_ack_done": False}
        goal["last_input"] = {"sha256": input_hash, "request": raw}
        operation = {"schema": OPERATION_SCHEMA, "operation_id": raw["input_id"], "event_id": raw["requirement_id"],
                     "expected_version": raw["expected_version"], "kind": kind, "value": value}
        result = self.store.apply(operation)
        return dict(result, schema=SCHEMA, personal_readback=self._project(result["readback"]["events"][0]),
                    state="PRIVATE_CAS_TRANSITION_READBACK", effect_ack_done=False)
