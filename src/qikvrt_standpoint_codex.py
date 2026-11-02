# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical QIKVRT V1 standpoint and lossless finite-set byte codec.

The shared signature describes the protocol. It is not a secret, an approval,
or the contents of a snapshot. Payloads are opaque bytes and are never executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import struct
from typing import Callable, Iterable

from src.qikvrt_effect_ack import canonical_json

VERSION = 1
SIGNATURE_BYTES = 400
STABLE_ID_BYTES = IDENTITY_BYTES = 32
SIGNATURE_MAGIC = b"QIKVRTSP"
SNAPSHOT_MAGIC = b"QIKVRTSS"
SIGNATURE_HEADER = struct.Struct(">8sHHHH32s")
SNAPSHOT_HEADER = struct.Struct(">8sHHQQ")
PAYLOAD_LENGTH = struct.Struct(">Q")
SIGNATURE_DOMAIN = b"QIKVRT-STANDPOINT-V1\x00"
IDENTITY_DOMAIN = b"QIKVRT-ELEMENT-V1\x00"

# Materialization of the declared invariants, not a recovered historical image.
SIGNATURE_DESCRIPTOR = {
    "codec": "QIKVRT",
    "element_binding": ["signature", "stable_id", "payload"],
    "element_identity": "SHA-256",
    "external_service_required": False,
    "format": VERSION,
    "order": "stable_id_bytes",
    "payload": "opaque_bytes",
    "serialization": "canonical_binary",
    "signature_bytes": SIGNATURE_BYTES,
    "validation": "fail_closed",
}
_SIGNATURE_PAYLOAD = canonical_json(SIGNATURE_DESCRIPTOR).encode("utf-8")
_SIGNATURE_PREFIX = struct.pack(
    ">8sHHHH", SIGNATURE_MAGIC, VERSION, SIGNATURE_BYTES,
    len(_SIGNATURE_PAYLOAD), 0,
)
QIKVRT_SIGNATURE = (
    _SIGNATURE_PREFIX
    + hashlib.sha256(
        SIGNATURE_DOMAIN + _SIGNATURE_PREFIX + _SIGNATURE_PAYLOAD
    ).digest()
    + _SIGNATURE_PAYLOAD
    + bytes(SIGNATURE_BYTES - SIGNATURE_HEADER.size - len(_SIGNATURE_PAYLOAD))
)
SIGNATURE_SHA256 = hashlib.sha256(QIKVRT_SIGNATURE).hexdigest()
MIN_ELEMENT_BYTES = SIGNATURE_BYTES + STABLE_ID_BYTES + IDENTITY_BYTES + 8
MIN_SNAPSHOT_BYTES = SNAPSHOT_HEADER.size + SIGNATURE_BYTES


class CodexError(ValueError):
    """Invalid, noncanonical, unsupported or over-budget input."""


def validate_signature(signature: bytes) -> None:
    """Accept only the exact V1 standpoint, including its zero padding."""
    if type(signature) is not bytes or len(signature) != SIGNATURE_BYTES:
        raise CodexError("signature must be exactly 400 immutable bytes")
    magic, version, size, length, flags, digest = SIGNATURE_HEADER.unpack_from(signature)
    if (magic, version, size, flags) != (SIGNATURE_MAGIC, VERSION, SIGNATURE_BYTES, 0):
        raise CodexError("unsupported signature header")
    if length != len(_SIGNATURE_PAYLOAD):
        raise CodexError("noncanonical signature payload length")
    end = SIGNATURE_HEADER.size + length
    payload = signature[SIGNATURE_HEADER.size:end]
    expected_digest = hashlib.sha256(SIGNATURE_DOMAIN + signature[:16] + payload).digest()
    if not hmac.compare_digest(digest, expected_digest):
        raise CodexError("signature payload digest mismatch")
    if signature[end:] != bytes(SIGNATURE_BYTES - end):
        raise CodexError("noncanonical signature padding")
    # Recomputing a digest does not authorize a different standpoint.
    if not hmac.compare_digest(signature, QIKVRT_SIGNATURE):
        raise CodexError("signature differs from the bound QIKVRT V1 standpoint")


def _identity(signature: bytes, stable_id: bytes, payload: bytes) -> bytes:
    digest = hashlib.sha256(IDENTITY_DOMAIN)
    digest.update(VERSION.to_bytes(2, "big"))
    digest.update(signature)
    digest.update(stable_id)
    digest.update(PAYLOAD_LENGTH.pack(len(payload)))
    digest.update(payload)
    return digest.digest()


@dataclass(frozen=True, slots=True)
class Element:
    """Immutable element: shared standpoint, stable label and content identity.

    Callers assign and persist a distinct 32-byte stable_id per logical element.
    Identical payloads may belong to different elements. A content change keeps
    the stable label and yields a new identity; the codec invents no labels.
    """

    stable_id: bytes
    payload: bytes
    signature: bytes = QIKVRT_SIGNATURE
    identity: bytes = field(init=False)

    def __post_init__(self) -> None:
        validate_signature(self.signature)
        if type(self.stable_id) is not bytes or len(self.stable_id) != STABLE_ID_BYTES:
            raise CodexError("stable_id must be exactly 32 immutable bytes")
        if type(self.payload) is not bytes or len(self.payload) > 2**64 - 1:
            raise CodexError("payload must be immutable bytes with a uint64 length")
        object.__setattr__(self, "identity", _identity(self.signature, self.stable_id, self.payload))


@dataclass(frozen=True, slots=True)
class Limits:
    """Local resource budget, separate from the V1 wire representation."""

    max_snapshot_bytes: int = 64 * 1024 * 1024
    max_elements: int = 100_000
    max_payload_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        values = (self.max_snapshot_bytes, self.max_elements, self.max_payload_bytes)
        if any(type(value) is not int or not 0 <= value <= 2**64 - 1 for value in values):
            raise CodexError("limits must be uint64 integers, not booleans")


DEFAULT_LIMITS = Limits()


def _limits(limits: Limits) -> None:
    if type(limits) is not Limits:
        raise CodexError("limits must be a Limits instance")


def serialize(elements: Iterable[Element], *, limits: Limits = DEFAULT_LIMITS) -> bytes:
    """Serialize a finite set in increasing stable-ID byte order.

    Snapshot, dump and serialization name this same wire representation.
    No timestamp, platform byte order, text normalization or hidden state enters
    the encoding. Nothing is returned until the complete set has been checked.
    """
    _limits(limits)
    if MIN_SNAPSHOT_BYTES > limits.max_snapshot_bytes:
        raise CodexError("snapshot exceeds byte budget")
    ordered = []
    stable_ids: set[bytes] = set()
    identities: set[bytes] = set()
    size = MIN_SNAPSHOT_BYTES
    try:
        iterator = iter(elements)
    except TypeError as exc:
        raise CodexError("elements must be iterable") from exc
    for element in iterator:
        if len(ordered) >= limits.max_elements:
            raise CodexError("element count exceeds budget")
        if type(element) is not Element:
            raise CodexError("snapshot members must be Element instances")
        if type(element.payload) is bytes and len(element.payload) > limits.max_payload_bytes:
            raise CodexError("payload exceeds byte budget")
        if type(element.payload) is bytes and size + MIN_ELEMENT_BYTES + len(element.payload) > limits.max_snapshot_bytes:
            raise CodexError("snapshot exceeds byte budget")
        # Validate again at the boundary, even for a frozen dataclass.
        checked = Element(element.stable_id, element.payload, element.signature)
        if type(element.identity) is not bytes or not hmac.compare_digest(element.identity, checked.identity):
            raise CodexError("element identity mismatch")
        if checked.stable_id in stable_ids or checked.identity in identities:
            raise CodexError("duplicate element identity or stable_id")
        if len(checked.payload) > limits.max_payload_bytes:
            raise CodexError("payload exceeds byte budget")
        size += MIN_ELEMENT_BYTES + len(checked.payload)
        if size > limits.max_snapshot_bytes:
            raise CodexError("snapshot exceeds byte budget")
        stable_ids.add(checked.stable_id)
        identities.add(checked.identity)
        ordered.append(checked)
    ordered.sort(key=lambda element: element.stable_id)
    records = b"".join(
        element.signature + element.stable_id + element.identity
        + PAYLOAD_LENGTH.pack(len(element.payload)) + element.payload
        for element in ordered
    )
    return (
        SNAPSHOT_HEADER.pack(SNAPSHOT_MAGIC, VERSION, SIGNATURE_BYTES, len(ordered), len(records))
        + QIKVRT_SIGNATURE + records
    )


def deserialize(data: bytes, *, limits: Limits = DEFAULT_LIMITS) -> tuple[Element, ...]:
    """Validate the whole canonical snapshot before exposing any element."""
    _limits(limits)
    if type(data) is not bytes:
        raise CodexError("snapshot must be immutable bytes")
    if not MIN_SNAPSHOT_BYTES <= len(data) <= limits.max_snapshot_bytes:
        raise CodexError("snapshot length is truncated or exceeds budget")
    magic, version, signature_size, count, body_size = SNAPSHOT_HEADER.unpack_from(data)
    if (magic, version, signature_size) != (SNAPSHOT_MAGIC, VERSION, SIGNATURE_BYTES):
        raise CodexError("unsupported snapshot header")
    if body_size != len(data) - MIN_SNAPSHOT_BYTES:
        raise CodexError("snapshot body length mismatch or trailing bytes")
    if count > limits.max_elements or count > body_size // MIN_ELEMENT_BYTES:
        raise CodexError("element count is impossible or exceeds budget")
    validate_signature(data[SNAPSHOT_HEADER.size:MIN_SNAPSHOT_BYTES])
    offset = MIN_SNAPSHOT_BYTES
    previous: bytes | None = None
    identities: set[bytes] = set()
    elements = []
    for _ in range(count):
        if len(data) - offset < MIN_ELEMENT_BYTES:
            raise CodexError("truncated element header")
        signature = data[offset:offset + SIGNATURE_BYTES]
        validate_signature(signature)
        offset += SIGNATURE_BYTES
        stable_id = data[offset:offset + STABLE_ID_BYTES]
        offset += STABLE_ID_BYTES
        identity = data[offset:offset + IDENTITY_BYTES]
        offset += IDENTITY_BYTES
        length = PAYLOAD_LENGTH.unpack_from(data, offset)[0]
        offset += PAYLOAD_LENGTH.size
        if previous is not None and stable_id <= previous:
            raise CodexError("duplicate stable_id or noncanonical element order")
        if length > limits.max_payload_bytes or length > len(data) - offset:
            raise CodexError("payload length is truncated or exceeds budget")
        element = Element(stable_id, data[offset:offset + length], signature)
        offset += length
        if not hmac.compare_digest(identity, element.identity):
            raise CodexError("element identity digest mismatch")
        if identity in identities:
            raise CodexError("duplicate element identity")
        identities.add(identity)
        previous = stable_id
        elements.append(element)
    if offset != len(data):
        raise CodexError("surplus elements or trailing bytes")
    return tuple(elements)


# The V1 standpoint and historical wire vectors above are immutable. This
# additive, explicitly selected profile binds rights inside EACH V1 element.
# Raw V1 snapshots are never silently admitted as licensed-profile snapshots.
LICENSED_SNAPSHOT_PREFIX = b"QIKVRTRS\x00\x01"
LICENSED_PAYLOAD_HEADER = struct.Struct(">8sHIIQ")
LICENSED_PAYLOAD_MAGIC = b"QIKVRTRP"
MAX_PROVENANCE_BYTES = 16 * 1024
RIGHTS_NOTICE = {
    "schema": "qikvrt_element_rights_v1",
    "technology_originator": "Ingolf Lohmann",
    "qikvrt_rights_holder": "Ingolf Lohmann",
    "required_notice": "Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.",
    "software_license": "PolyForm-Noncommercial-1.0.0",
    "software_license_url": "https://polyformproject.org/licenses/noncommercial/1.0.0",
    "software_license_text": '# PolyForm Noncommercial License 1.0.0\n\n<https://polyformproject.org/licenses/noncommercial/1.0.0>\n\n## Acceptance\n\nIn order to get any license under these terms, you must agree\nto them as both strict obligations and conditions to all\nyour licenses.\n\n## Copyright License\n\nThe licensor grants you a copyright license for the\nsoftware to do everything you might do with the software\nthat would otherwise infringe the licensor\'s copyright\nin it for any permitted purpose.  However, you may\nonly distribute the software according to [Distribution\nLicense](#distribution-license) and make changes or new works\nbased on the software according to [Changes and New Works\nLicense](#changes-and-new-works-license).\n\n## Distribution License\n\nThe licensor grants you an additional copyright license\nto distribute copies of the software.  Your license\nto distribute covers distributing the software with\nchanges and new works permitted by [Changes and New Works\nLicense](#changes-and-new-works-license).\n\n## Notices\n\nYou must ensure that anyone who gets a copy of any part of\nthe software from you also gets a copy of these terms or the\nURL for them above, as well as copies of any plain-text lines\nbeginning with `Required Notice:` that the licensor provided\nwith the software.  For example:\n\n> Required Notice: Copyright Yoyodyne, Inc. (http://example.com)\n\n## Changes and New Works License\n\nThe licensor grants you an additional copyright license to\nmake changes and new works based on the software for any\npermitted purpose.\n\n## Patent License\n\nThe licensor grants you a patent license for the software that\ncovers patent claims the licensor can license, or becomes able\nto license, that you would infringe by using the software.\n\n## Noncommercial Purposes\n\nAny noncommercial purpose is a permitted purpose.\n\n## Personal Uses\n\nPersonal use for research, experiment, and testing for\nthe benefit of public knowledge, personal study, private\nentertainment, hobby projects, amateur pursuits, or religious\nobservance, without any anticipated commercial application,\nis use for a permitted purpose.\n\n## Noncommercial Organizations\n\nUse by any charitable organization, educational institution,\npublic research organization, public safety or health\norganization, environmental protection organization,\nor government institution is use for a permitted purpose\nregardless of the source of funding or obligations resulting\nfrom the funding.\n\n## Fair Use\n\nYou may have "fair use" rights for the software under the\nlaw. These terms do not limit them.\n\n## No Other Rights\n\nThese terms do not allow you to sublicense or transfer any of\nyour licenses to anyone else, or prevent the licensor from\ngranting licenses to anyone else.  These terms do not imply\nany other licenses.\n\n## Patent Defense\n\nIf you make any written claim that the software infringes or\ncontributes to infringement of any patent, your patent license\nfor the software granted under these terms ends immediately. If\nyour company makes such a claim, your patent license ends\nimmediately for work on behalf of your company.\n\n## Violations\n\nThe first time you are notified in writing that you have\nviolated any of these terms, or done anything with the software\nnot covered by your licenses, your licenses can nonetheless\ncontinue if you come into full compliance with these terms,\nand take practical steps to correct past violations, within\n32 days of receiving notice.  Otherwise, all your licenses\nend immediately.\n\n## No Liability\n\n***As far as the law allows, the software comes as is, without\nany warranty or condition, and the licensor will not be liable\nto you for any damages arising out of these terms or the use\nor nature of the software, under any kind of legal claim.***\n\n## Definitions\n\nThe **licensor** is the individual or entity offering these\nterms, and the **software** is the software the licensor makes\navailable under these terms.\n\n**You** refers to the individual or entity agreeing to these\nterms.\n\n**Your company** is any legal entity, sole proprietorship,\nor other kind of organization that you work for, plus all\norganizations that have control over, are under the control of,\nor are under common control with that organization.  **Control**\nmeans ownership of substantially all the assets of an entity,\nor the power to direct its management and policies by vote,\ncontract, or otherwise.  Control can be direct or indirect.\n\n**Your licenses** are all the licenses granted to you for the\nsoftware under these terms.\n\n**Use** means anything you do with the software requiring one\nof your licenses.\n',
    "documentation_license": "CC-BY-NC-ND-4.0",
    "documentation_license_url": "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode",
    "private_noncommercial_license_fee_eur": 0,
    "ordinary_commercial_use": "Separate written paid agreement with Ingolf Lohmann required; price and scope are specified in that agreement, not by this element.",
    "rights_boundary": "Applies only to QIK-VRT material the licensor can license. More specific file notices, historical Apache/MIT grants, third-party and payload rights, statutory exceptions and all PolyForm permitted purposes remain unchanged. No automatic ownership of payloads, payment, contract or natural-person authentication is created.",
}
RIGHTS_BYTES = canonical_json(RIGHTS_NOTICE).encode("utf-8")
RIGHTS_SHA256 = hashlib.sha256(RIGHTS_BYTES).hexdigest()


def _provenance(attribution: str, license_id: str, source: str) -> bytes:
    fields = {"attribution": attribution, "license": license_id, "source": source}
    if any(type(v) is not str or not v.strip() or len(v) > 4096
           for v in fields.values()):
        raise CodexError("PAYLOAD_PROVENANCE_REQUIRED")
    try:
        encoded = canonical_json(fields).encode("utf-8")
    except UnicodeError as exc:
        raise CodexError("INVALID_PROVENANCE_UNICODE") from exc
    if len(encoded) > MAX_PROVENANCE_BYTES:
        raise CodexError("PROVENANCE_BUDGET_EXCEEDED")
    return encoded


def licensed_element(stable_id: bytes, payload: bytes, *,
                     payload_attribution: str, payload_license: str,
                     payload_source: str) -> Element:
    """Create a rights-bearing element without executing or relicensing payload.

    Provenance is the caller's declaration, not an independently verified
    authorship certificate. Rights text is persisted, not merely linked.
    """
    Element(stable_id, payload)  # Validate the unchanged V1 types first.
    provenance = _provenance(payload_attribution, payload_license, payload_source)
    bound_payload = (LICENSED_PAYLOAD_HEADER.pack(
        LICENSED_PAYLOAD_MAGIC, 1, len(RIGHTS_BYTES), len(provenance), len(payload)
    ) + RIGHTS_BYTES + provenance + payload)
    return Element(stable_id, bound_payload)


def licensed_payload(element: Element) -> tuple[bytes, dict[str, str]]:
    """Validate again at the boundary, then expose opaque data and provenance."""
    if type(element) is not Element:
        raise CodexError("LICENSED_ELEMENT_REQUIRED")
    checked = Element(element.stable_id, element.payload, element.signature)
    if type(element.identity) is not bytes or not hmac.compare_digest(
            checked.identity, element.identity):
        raise CodexError("ELEMENT_IDENTITY_MISMATCH")
    data = checked.payload
    if len(data) < LICENSED_PAYLOAD_HEADER.size:
        raise CodexError("RIGHTS_ENVELOPE_REQUIRED")
    magic, version, notice_len, provenance_len, payload_len = LICENSED_PAYLOAD_HEADER.unpack_from(data)
    if (magic, version, notice_len) != (LICENSED_PAYLOAD_MAGIC, 1, len(RIGHTS_BYTES)):
        raise CodexError("RIGHTS_PROFILE_MISMATCH")
    start = LICENSED_PAYLOAD_HEADER.size
    end = start + notice_len
    if (provenance_len > MAX_PROVENANCE_BYTES
            or end + provenance_len + payload_len != len(data)):
        raise CodexError("RIGHTS_ENVELOPE_LENGTH_MISMATCH")
    if not hmac.compare_digest(data[start:end], RIGHTS_BYTES):
        raise CodexError("RIGHTS_NOTICE_MISMATCH")
    metadata = data[end:end + provenance_len]
    try:
        provenance = json.loads(metadata)
    except (ValueError, UnicodeError) as exc:
        raise CodexError("INVALID_PAYLOAD_PROVENANCE") from exc
    if type(provenance) is not dict or set(provenance) != {"attribution", "license", "source"}:
        raise CodexError("INVALID_PAYLOAD_PROVENANCE")
    if metadata != _provenance(provenance["attribution"], provenance["license"], provenance["source"]):
        raise CodexError("NONCANONICAL_PAYLOAD_PROVENANCE")
    return data[end + provenance_len:], provenance


def _licensed_limits(limits: Limits) -> Limits:
    _limits(limits)
    if limits.max_snapshot_bytes < len(LICENSED_SNAPSHOT_PREFIX):
        raise CodexError("LICENSED_SNAPSHOT_BUDGET_EXCEEDED")
    return Limits(limits.max_snapshot_bytes - len(LICENSED_SNAPSHOT_PREFIX),
                  limits.max_elements, limits.max_payload_bytes)


def serialize_licensed(elements: Iterable[Element], *, limits: Limits = DEFAULT_LIMITS) -> bytes:
    """Use the existing bounded, ordered V1 codec after checking each envelope."""
    inner_limits = _licensed_limits(limits)
    def checked_members():
        for element in elements:
            licensed_payload(element)
            yield element
    try:
        body = serialize(checked_members(), limits=inner_limits)
    except TypeError as exc:
        raise CodexError("LICENSED_ELEMENTS_MUST_BE_ITERABLE") from exc
    return LICENSED_SNAPSHOT_PREFIX + body


def deserialize_licensed(data: bytes, *, limits: Limits = DEFAULT_LIMITS) -> tuple[Element, ...]:
    """Fail closed on downgrade, notice removal, corruption and resource excess."""
    inner_limits = _licensed_limits(limits)
    if type(data) is not bytes or not data.startswith(LICENSED_SNAPSHOT_PREFIX):
        raise CodexError("LICENSED_SNAPSHOT_PROFILE_REQUIRED")
    if len(data) > limits.max_snapshot_bytes:
        raise CodexError("LICENSED_SNAPSHOT_BUDGET_EXCEEDED")
    elements = deserialize(data[len(LICENSED_SNAPSHOT_PREFIX):], limits=inner_limits)
    for element in elements:
        licensed_payload(element)
    return elements


def inspect_licensed(data: bytes, *, expected_sha256: str | None = None,
                     limits: Limits = DEFAULT_LIMITS,
                     signal: Callable[[dict], None] | None = None) -> dict:
    """Return a portable diagnostic; optionally submit it to an admitted sink.

    Sink return is NOT delivery/receiver/effect acknowledgement. Failure to
    signal is explicit and never changes a detected rejection into success.
    An external digest must come from a separately trusted source. Public
    standpoint and unkeyed hashes alone do not authenticate an adversarially
    rewritten payload or identify the natural person Ingolf Lohmann.
    """
    report = {"schema": "qikvrt_element_diagnostic_v1", "state": "UNVERIFIED",
              "code": "INPUT_UNAVAILABLE", "subject_sha256": None,
              "elements": 0, "signal_state": "NOT_REQUESTED",
              "effect_ack_done": False, "origin_authenticated": False}
    if type(data) is bytes:
        report["subject_sha256"] = hashlib.sha256(data).hexdigest()
        try:
            # Invalid local budgets and trust references are checker failures,
            # not evidence that the target bytes themselves are corrupt.
            try:
                _licensed_limits(limits)
                if expected_sha256 is not None and (
                        type(expected_sha256) is not str or len(expected_sha256) != 64
                        or any(c not in "0123456789abcdef" for c in expected_sha256)):
                    raise CodexError("TRUSTED_DIGEST_INVALID")
            except CodexError:
                report["code"] = "CHECKER_CONFIGURATION_INVALID"
                raise RuntimeError("checker configuration unavailable") from None
            if expected_sha256 is not None:
                if not hmac.compare_digest(report["subject_sha256"], expected_sha256):
                    raise CodexError("TRUSTED_DIGEST_MISMATCH")
            elements = deserialize_licensed(data, limits=limits)
            report.update(state="VERIFIED", code="LICENSED_PROFILE_VALID", elements=len(elements))
        except CodexError as exc:
            report.update(state="REJECTED", code="LICENSED_PROFILE_REJECTED", reason=str(exc))
        except Exception:
            if report["code"] != "CHECKER_CONFIGURATION_INVALID":
                report["code"] = "CHECKER_FAILED"
    if signal is not None:
        try:
            signal(dict(report))
            report["signal_state"] = "SUBMITTED_UNCONFIRMED"
        except Exception:
            report["signal_state"] = "SIGNAL_FAILED"
    return report
