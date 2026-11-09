#!/usr/bin/env python3
"""Experimental mutually authenticated loopback HTTPS transport, NOT EAP DONE.

Server and client are distinct operating-system processes and use distinct
persistent directories. The test CA is ephemeral; no private key belongs in Git.
No externally deployed node is claimed by this module.
"""
from __future__ import annotations
import argparse
import http.client
import json
import ssl
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from two_way_reference import Receiver, Sender, canonical, Refusal, ZERO

MAX_BODY = 65536


def certificate_common_name(cert: dict) -> str | None:
    for rdn in cert.get('subject', ()):
        for key, val in rdn:
            if key == 'commonName':
                return val
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, fmt, *args):
        pass

    def respond(self, status, payload):
        body = canonical(payload)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        certificate = self.connection.getpeercert()
        if certificate_common_name(certificate or {}) != self.server.peer_name:
            self.respond(403, {'error': 'CLIENT_IDENTITY_NOT_ADMITTED', 'effect_ack_done': False})
            return False
        return True

    def do_POST(self):
        if self.path != '/v1/events':
            return self.respond(404, {'error': 'NO_SUCH_ROUTE'})
        if not self.authorized():
            return
        raw_size = self.headers.get('Content-Length', '')
        if not raw_size.isdecimal() or int(raw_size) > MAX_BODY or int(raw_size) < 2:
            return self.respond(413, {'error': 'INVALID_CONTENT_LENGTH'})
        raw = self.rfile.read(int(raw_size))
        try:
            obj = json.loads(raw)
            if canonical(obj) != raw:
                raise Refusal('NONCANONICAL_EVENT')
            receipt = self.server.receiver.accept(obj)
        except (ValueError, KeyError, TypeError, UnicodeDecodeError, OverflowError) as exc:
            return self.respond(409, {'error': str(exc), 'effect_ack_done': False})
        return self.respond(200, {'receipt': receipt, 'effect_ack_done': False})

    def do_GET(self):
        if not self.authorized():
            return
        if self.path == '/health':
            return self.respond(200, {'server': self.server.receiver.node_id, 'ready': True,
                                      'effect_ack_done': False, 'scope': 'EPHEMERAL_LOCAL_TEST'})
        if not self.path.startswith('/v1/receipts/'):
            return self.respond(404, {'error': 'NO_SUCH_ROUTE'})
        event_id = self.path.removeprefix('/v1/receipts/')
        if not event_id or '/' in event_id or '%' in event_id or len(event_id)>128:
            return self.respond(400, {'error': 'INVALID_EVENT_ID'})
        try:
            receipt = self.server.receiver.read_receipt(event_id)
        except (ValueError, KeyError, TypeError) as exc:
            return self.respond(404 if str(exc) == 'RECEIPT_NOT_FOUND' else 409,
                                {'error': str(exc), 'effect_ack_done': False})
        return self.respond(200, {'receipt': receipt, 'effect_ack_done': False})


def serve(*, host, port, ca, cert, key, state, source_head, admitted):
    server = HTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.peer_name = 'node-a'
    server.receiver = Receiver(Path(state), node_id='node-b', accepted_sender='node-a',
                               expected_head=source_head, admission=admitted)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    ctx.load_verify_locations(cafile=ca)
    ctx.verify_mode = ssl.CERT_REQUIRED
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    try:
        print('READY', flush=True)
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


def request(*, port: int, ca: str, cert: str | None, key: str | None,
            method: str, path: str, data: dict | None = None):
    context = ssl.create_default_context(cafile=ca)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if cert:
        context.load_cert_chain(cert, key)
    client = http.client.HTTPSConnection('localhost', port, context=context, timeout=3)
    try:
        body = canonical(data) if data is not None else None
        client.request(method, path, body=body, headers={'Content-Type': 'application/json'} if body else {})
        res = client.getresponse()
        out = res.read(MAX_BODY + 1)
        if len(out) > MAX_BODY:
            raise Refusal('OVERSIZE_REMOTE_RESPONSE')
        return res.status, json.loads(out)
    finally:
        client.close()


def round_trip(*, root: Path, port: int, ca: str, cert: str, key: str,
               head: str, event_id: str, kind: str, payload: bytes):
    sender = Sender(root, node_id='node-a', receiver='node-b', source_head=head)
    event = sender.prepare(event_id=event_id, kind=kind, raw=payload)
    code, answer = request(port=port, ca=ca, cert=cert, key=key,
                           method='POST', path='/v1/events', data=event)
    if code != 200 or answer.get('effect_ack_done') is not False:
        raise Refusal('RECEIVER_NOT_VERIFIED')
    readback = lambda ident: request(port=port, ca=ca, cert=cert, key=key,
                                    method='GET', path='/v1/receipts/' + ident)[1]['receipt']
    return sender.verify_return(event, readback)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('role', choices=['server', 'client'])
    for name in ('ca', 'cert', 'key', 'state', 'head'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--admitted', action='store_true')
    p.add_argument('--event-id', default='claim-1')
    p.add_argument('--payload', default='original claim')
    p.add_argument('--kind', default='CLAIM')
    a = p.parse_args()
    if a.role == 'server':
        serve(host='127.0.0.1', port=a.port, ca=a.ca, cert=a.cert, key=a.key,
              state=a.state, source_head=a.head, admitted=a.admitted)
    else:
        result = round_trip(root=Path(a.state),port=a.port,ca=a.ca,cert=a.cert,
                            key=a.key,head=a.head,event_id=a.event_id,
                            kind=a.kind,payload=a.payload.encode('utf-8'))
        print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    main()
