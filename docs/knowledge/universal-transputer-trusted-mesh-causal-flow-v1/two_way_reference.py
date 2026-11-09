#!/usr/bin/env python3
"""Bounded, offline two-store reference for a bidirectional evidence round trip.

This is a research simulator, not a network Mesh, trusted hardware, or EFFECT_ACK.
Source and destination are distinct directories; each file is fsync-ed before
reporting a verified receipt. No credentials, network, or host action is used.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

SCHEMA = 'qikvrt-two-way-observation/v1'
ZERO = '0' * 64

class Refusal(ValueError):
    pass


def canonical(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.tmp-', delete=False) as tmp:
        name = Path(tmp.name)
        try:
            tmp.write(canonical(data))
            tmp.flush()
            os.fsync(tmp.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    try:
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        name.unlink(missing_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def observation(*, sender: str, receiver: str, source_head: str, sequence: int,
                event_id: str, kind: str, raw: bytes, previous: str = ZERO) -> dict:
    if kind not in ('CLAIM', 'COUNTER_EVIDENCE') or not isinstance(raw, bytes):
        raise Refusal('INVALID_EVENT_KIND_OR_BYTES')
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise Refusal('INVALID_SEQUENCE')
    if not isinstance(event_id, str) or not event_id:
        raise Refusal('INVALID_EVENT_ID')
    return dict(schema=SCHEMA, sender=sender, receiver=receiver, source_head=source_head,
                sequence=sequence, event_id=event_id, kind=kind,
                payload_base64=base64.b64encode(raw).decode('ascii'), payload_sha256=digest(raw),
                previous_receipt_sha256=previous)


class Receiver:
    def __init__(self, root: Path, *, node_id: str, accepted_sender: str,
                 expected_head: str, admission: bool = True):
        self.root = root
        self.node_id = node_id
        self.accepted_sender = accepted_sender
        self.expected_head = expected_head
        self.admission = admission
        self.ledger = root / 'received.json'

    def _state(self):
        if self.ledger.exists():
            s = load_json(self.ledger)
            self._verify_ledger(s)
            return s
        return {'schema': SCHEMA, 'node_id': self.node_id, 'events': [],
                'last_receipt_sha256': ZERO}

    def _verify_ledger(self, state):
        if state.get('schema') != SCHEMA or state.get('node_id') != self.node_id:
            raise Refusal('LEDGER_IDENTITY_MISMATCH')
        prev = ZERO
        seen = set()
        for index, entry in enumerate(state.get('events', []), 1):
            e, receipt = entry['event'], entry['receipt']
            if e.get('sequence') != index or e.get('previous_receipt_sha256') != prev:
                raise Refusal('STORED_CHAIN_INVALID')
            if e.get('event_id') in seen:
                raise Refusal('STORED_DUPLICATE_EVENT')
            seen.add(e['event_id'])
            self._check_event(e)
            self._verify_receipt(e, receipt)
            prev = digest(canonical(receipt))
        if state.get('last_receipt_sha256') != prev:
            raise Refusal('STORED_HEAD_INVALID')

    def _check_event(self, e):
        if e.get('schema') != SCHEMA or e.get('sender') != self.accepted_sender or e.get('receiver') != self.node_id:
            raise Refusal('INVALID_SOURCE_IDENTITY')
        if e.get('source_head') != self.expected_head:
            raise Refusal('WRONG_SOURCE_HEAD')
        if e.get('kind') not in ('CLAIM', 'COUNTER_EVIDENCE'):
            raise Refusal('UNKNOWN_EVIDENCE_KIND')
        try:
            raw = base64.b64decode(e['payload_base64'], validate=True)
        except (ValueError, KeyError):
            raise Refusal('INVALID_PAYLOAD') from None
        if base64.b64encode(raw).decode('ascii') != e['payload_base64'] or digest(raw) != e.get('payload_sha256'):
            raise Refusal('PAYLOAD_DIGEST_MISMATCH')
        if not isinstance(e.get('event_id'), str) or not e['event_id']:
            raise Refusal('INVALID_EVENT_ID')
        if not isinstance(e.get('sequence'), int) or isinstance(e['sequence'], bool):
            raise Refusal('INVALID_SEQUENCE')

    @staticmethod
    def _verify_receipt(e, receipt):
        if (receipt.get('kind') != 'RECEIVED_VERIFIED' or receipt.get('schema') != SCHEMA or
            receipt.get('event_digest') != digest(canonical(e)) or
            receipt.get('event_id') != e['event_id'] or
            receipt.get('payload_sha256') != e['payload_sha256'] or
            receipt.get('source_head') != e['source_head'] or
            receipt.get('receiver') != e['receiver'] or
            receipt.get('sequence') != e['sequence'] or
            receipt.get('effect_ack_done') is not False):
            raise Refusal('RECEIPT_BINDING_MISMATCH')

    def accept(self, e: dict) -> dict:
        if not self.admission:
            raise Refusal('NOT_ADMITTED')
        self._check_event(e)
        s = self._state()
        seen = {entry['event']['event_id']: entry for entry in s['events']}
        if e['event_id'] in seen:
            if seen[e['event_id']]['event'] != e:
                raise Refusal('DUPLICATE_ID_CHANGED_CONTENT')
            return seen[e['event_id']]['receipt']  # idempotent replay, no second effect
        if e['sequence'] != len(s['events']) + 1:
            raise Refusal('SEQUENCE_GAP_OR_REPLAY')
        if e['previous_receipt_sha256'] != s['last_receipt_sha256']:
            raise Refusal('STALE_PREVIOUS_RECEIPT')
        receipt = dict(schema=SCHEMA, kind='RECEIVED_VERIFIED', event_id=e['event_id'],
                       event_digest=digest(canonical(e)), payload_sha256=e['payload_sha256'],
                       source_head=e['source_head'], receiver=self.node_id,
                       sequence=e['sequence'], effect_ack_done=False)
        s['events'].append(dict(event=e, receipt=receipt))
        s['last_receipt_sha256'] = digest(canonical(receipt))
        atomic_json(self.ledger, s)
        return receipt

    def read_receipt(self, event_id: str) -> dict:
        s = self._state()  # independent file read and complete chain verification
        for entry in s['events']:
            if entry['event']['event_id'] == event_id:
                return entry['receipt']
        raise Refusal('RECEIPT_NOT_FOUND')


class Sender:
    def __init__(self, root: Path, *, node_id: str, receiver: str, source_head: str):
        self.root, self.node_id, self.receiver, self.source_head = root, node_id, receiver, source_head
        self.outbox = root / 'outbox.json'

    def prepare(self, *, event_id: str, kind: str, raw: bytes) -> dict:
        state = load_json(self.outbox) if self.outbox.exists() else dict(events=[], last_receipt_sha256=ZERO)
        if any(e['event_id'] == event_id for e in state['events']):
            raise Refusal('SENDER_DUPLICATE_EVENT_ID')
        e = observation(sender=self.node_id, receiver=self.receiver,source_head=self.source_head,
                        sequence=len(state['events']) + 1,event_id=event_id,kind=kind,raw=raw,
                        previous=state['last_receipt_sha256'])
        # A provisional outbound item is written, but never claims reception.
        state['events'].append(e)
        atomic_json(self.outbox, state)
        return e

    def verify_return(self, e: dict, remote_receipt_readback) -> dict:
        receipt = remote_receipt_readback(e['event_id'])
        Receiver._verify_receipt(e, receipt)
        state = load_json(self.outbox)
        if not any(candidate == e for candidate in state['events']):
            raise Refusal('SENDER_EVENT_MISMATCH')
        state['last_receipt_sha256'] = digest(canonical(receipt))
        atomic_json(self.outbox, state)
        return dict(receipt_verified=True, recorded_event_id=e['event_id'],
                    effect_ack_done=False, payload_sha256=e['payload_sha256'])
