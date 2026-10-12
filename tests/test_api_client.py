#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Client-side transport-boundary tests for the local dispatch adapter."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import qikvrt_api_client as client  # noqa: E402


class ApiClientTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_dir = directory.name
        patch = mock.patch.dict(os.environ, {"QIKVRT_API_CLIENT_STATE_DIR": directory.name})
        patch.start()
        self.addCleanup(patch.stop)

    def invoke(self, *arguments: str) -> int:
        argv = ["qikvrt_api_client.py", "--owner", "owner", "--repo", "repo", *arguments]
        with mock.patch.object(sys, "argv", argv):
            return client.main()

    def test_non_loopback_cleartext_endpoint_is_rejected_before_network(self) -> None:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke(
                        "--base-url", "http://example.test:8766",
                        "--operation", "release_status",
                        "--request-id", "cleartext-rejected",
                    )
        self.assertEqual(raised.exception.code, 2)

    def test_transport_failure_returns_blocking_exit_without_traceback(self) -> None:
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.URLError("connection refused")
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(
                client.urllib.request,
                "build_opener",
                return_value=opener,
            ):
                with contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()):
                    result = self.invoke(
                        "--operation", "release_status",
                        "--request-id", "transport-failure",
                    )
        self.assertEqual(result, 1)
        self.assertIn("BLOCK API request failed", stderr.getvalue())

    def test_redirects_are_never_followed(self) -> None:
        handler = client.NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                mock.Mock(), None, 302, "Found", {}, "https://other.invalid/"
            )
        )

    def test_file_reader_rejects_symlinks_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.bin"
            target.write_bytes(b"12345")
            link = root / "link.bin"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(OSError):
                    client.read_regular_file(link, max_bytes=10)
            with self.assertRaisesRegex(OSError, "exceeds"):
                client.read_regular_file(target, max_bytes=4)


class ApiClientEndOfActionConformanceTests(unittest.TestCase):
    """Direct CLI obligations executed as ordinary assertions after repair.

    These execute the actual client with a recorded, deterministic transport.
    They do not execute a vendor AI session or prove public product delivery.
    The Owner contract and shared receipt validator remain the sole authority.
    """

    setUp = ApiClientTests.setUp

    class Response:
        def __init__(self, raw: bytes, url: str) -> None:
            self.raw, self.url = raw, url
            self.status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self, limit: int) -> bytes:
            return self.raw[:limit]

        def geturl(self) -> str:
            return self.url

    def transport(self, *, failure: bool = False):
        requests = []

        def open_request(request, **_):
            requests.append(request)
            url = request.full_url
            if request.get_method() == "POST":
                if failure:
                    raise urllib.error.HTTPError(
                        url, 403, "Forbidden", {},
                        io.BytesIO(b'{"error":"unchanged admission denied"}'),
                    )
                raw = b'{"handler_result":{"effect_state":"EFFECT_ACK_DONE"}}'
            elif url.startswith("https://api.github.com/"):
                raw = json.dumps({
                    "sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}},
                }).encode("utf-8")
            else:
                raw = b"fixture: public response, not productive delivery proof"
            return self.Response(raw, url)

        opener = mock.Mock()
        opener.open.side_effect = open_request
        return opener, requests

    def invoke_actual_client(self, *arguments: str) -> int:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return ApiClientTests.invoke(
                    self, "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--operation", "verify", "--request-id", "same-causal-subject",
                    "--dry-run", "false", "--accept-effect",
                    *arguments,
                )

    def assert_closing_reads(self, requests, *, repository: bool = True) -> None:
        from tools.ai_handoff import client_end_of_action_domain
        post = next(i for i, request in enumerate(requests)
                    if request.get_method() == "POST")
        closing = requests[post + 1:]
        repository_reads = [request for request in closing
                            if request.get_method() == "GET"
                            and request.full_url ==
                            "https://api.github.com/repos/ingolf-lohmann/qik-vrt/commits/main"]
        if repository:
            self.assertTrue(repository_reads, "no fresh repository HEAD/TREE read after action")
        public_url = "https://" + client_end_of_action_domain() + "/"
        self.assertTrue(
            any(request.get_method() == "GET" and request.full_url == public_url
                for request in closing),
            "no fresh exact-host public delivery read after action",
        )
        for request in closing:
            if request.full_url == public_url:
                self.assertIsNone(request.get_header("Authorization"))

    def test_scoped_handler_done_does_not_replace_fresh_client_closure(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests)

    def test_http_error_still_requires_fresh_repository_and_delivery_readback(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)

    def test_success_still_requires_fresh_exact_host_public_delivery_readback(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests, repository=False)

    def test_same_failed_subject_without_new_cause_does_not_post_again(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            self.assertEqual(self.invoke_actual_client(), 1)
        posts = [request for request in requests if request.get_method() == "POST"]
        self.assertEqual(len(posts), 1, "unchanged failure submitted twice without new cause")

    def test_repository_parser_recursion_failure_cannot_skip_public_closing_readback(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def deeply_nested_repository(request, **kwargs):
            response = original(request, **kwargs)
            if request.full_url.startswith("https://api.github.com/"):
                response.raw = b'[' * 2500 + b'0' + b']' * 2500
            return response

        opener.open.side_effect = deeply_nested_repository
        parse = client.unique_json

        def exhausted_decoder(raw):
            if raw.startswith(b'['):
                raise RecursionError("fixture: decoder recursion limit")
            return parse(raw)

        # Decoder limits vary between supported Python builds. Inject the
        # parser's resource failure to verify the actual closing control path.
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "unique_json", side_effect=exhausted_decoder):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)
        self.assertEqual(sum(request.get_method() == "GET" for request in requests), 2)

    def test_scoped_done_remains_continue_and_reuses_shared_closure_validator(self) -> None:
        opener, requests = self.transport()
        validate = client.validate_client_readback
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "validate_client_readback", wraps=validate) as gate:
            self.assertEqual(self.invoke_actual_client(), 20)
        gate.assert_called_once()
        readback, subject, window = gate.call_args.args
        self.assertEqual(subject["head"], "a" * 40)
        self.assertEqual(subject["tree"], "b" * 40)
        self.assertEqual(readback["delivery"]["state"], "PENDING")
        self.assertFalse(readback["delivery"]["working_software"])
        self.assertGreater(readback["repository"]["observed_at"], window["completed_at"])
        self.assert_closing_reads(requests)

    def test_repository_read_failure_still_gets_public_origin_and_never_done(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def broken_repository(request, **kwargs):
            if request.get_method() == "GET" and request.full_url.startswith("https://api.github.com/"):
                requests.append(request)
                raise urllib.error.URLError("unavailable")
            return original(request, **kwargs)

        opener.open.side_effect = broken_repository
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)

    def test_other_origin_final_url_and_duplicate_repository_json_are_rejected(self) -> None:
        for kind in ("delivery", "repository"):
            with self.subTest(kind=kind):
                opener, requests = self.transport()
                original = opener.open.side_effect

                def invalid_readback(request, **kwargs):
                    response = original(request, **kwargs)
                    if request.get_method() == "GET":
                        if kind == "delivery" and request.full_url == "https://raumzeitterminal.de/":
                            response.url = "https://other.invalid/"
                        elif kind == "repository" and request.full_url.startswith("https://api.github.com/"):
                            response.raw = b'{"sha":"a","sha":"b"}'
                    return response

                opener.open.side_effect = invalid_readback
                with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                    self.assertEqual(self.invoke_actual_client(), 1)
                self.assert_closing_reads(requests)

    def test_adapter_token_is_never_forwarded_to_closing_origins(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        for request in requests:
            if request.get_method() == "GET":
                self.assertIsNone(request.get_header("Authorization"))

    def test_failure_survives_new_process_and_new_request_id(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        program = '''
import json
from unittest import mock
from tests.test_api_client import ApiClientEndOfActionConformanceTests
from scripts import qikvrt_api_client as client
fixture = ApiClientEndOfActionConformanceTests()
opener, requests = fixture.transport(failure=True)
with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
    result = fixture.invoke_actual_client("--request-id", "new-clock-and-request-id")
print(json.dumps({"exit": result, "posts": sum(r.get_method() == "POST" for r in requests),
                  "gets": sum(r.get_method() == "GET" for r in requests)}))
'''
        completed = subprocess.run([sys.executable, "-B", "-c", program], cwd=REPOSITORY_ROOT,
                                   env=dict(os.environ), capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"exit": 1, "posts": 0, "gets": 2})
        journal = next(Path(self.state_dir).glob("*.json")).read_text()
        self.assertNotIn("test-token", journal)
        self.assertNotIn("payload_b64", journal)
        self.assertEqual(os.stat(next(Path(self.state_dir).glob("*.json"))).st_mode & 0o777, 0o600)

    def test_new_cause_admits_one_attempt_but_clocks_do_not(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            path = next(Path(self.state_dir).glob("*.json"))
            previous = json.loads(path.read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(previous, observed_at="later", repository_head="c" * 40)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
            evidence.write_text(json.dumps(dict(previous, cause="f" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)

    def test_successful_and_changed_subject_requests_are_not_suppressed(self) -> None:
        for failure in (False, True):
            with self.subTest(failure=failure):
                opener, requests = self.transport(failure=failure)
                with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                    self.invoke_actual_client("--artifact-id", "first" + str(failure))
                    arguments = ("--artifact-id", "second" + str(failure)) if failure else ("--artifact-id", "firstFalse")
                    self.invoke_actual_client(*arguments)
                self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)

    def test_timeout_is_ambiguous_and_new_cause_does_not_hide_missing_effect_readback(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def timeout(request, **kwargs):
            if request.get_method() == "POST":
                requests.append(request)
                raise TimeoutError()
            return original(request, **kwargs)

        opener.open.side_effect = timeout
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            previous = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(previous, cause="f" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
        self.assertEqual(sum(r.get_method() == "GET" for r in requests), 4)

    def test_state_write_failure_after_post_preserves_count_and_still_closes(self) -> None:
        opener, requests = self.transport()
        writer = client.atomic_write_bytes
        writes = 0

        def fail_second_write(*args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("disk unavailable")
            return writer(*args, **kwargs)

        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "atomic_write_bytes", side_effect=fail_second_write):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)
        journal = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
        self.assertEqual(journal["status"], "in_flight")
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)

    def test_new_cause_cannot_bypass_explicit_effect_acceptance(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            current = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(current, cause="f" * 64)))
            argv = ["qikvrt_api_client.py", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--operation", "verify", "--request-id", "same-causal-subject", "--dry-run", "false",
                    "--retry-evidence-file", str(evidence)]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    client.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)

    def test_corrupt_or_symlink_state_blocks_before_post_and_still_closes(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            path = next(Path(self.state_dir).glob("*.json"))
            path.write_text("corrupt")
            self.assertEqual(self.invoke_actual_client(), 1)
            victim = Path(self.state_dir) / "victim.data"
            victim.write_text("untouched")
            path.unlink()
            path.symlink_to(victim)
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
        self.assertEqual(sum(r.get_method() == "GET" for r in requests), 6)
        self.assertEqual(victim.read_text(), "untouched")

    def continuation_work(self) -> dict:
        return json.loads((Path(self.state_dir) / "CONTINUATION.data").read_text())

    def test_interrupted_intent_is_inherited_even_when_next_request_changes(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect
        interrupt = True

        def interrupted(request, **kwargs):
            if interrupt and request.get_method() == "POST":
                requests.append(request)
                raise KeyboardInterrupt()
            return original(request, **kwargs)

        opener.open.side_effect = interrupted
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke_actual_client("--artifact-id", "interrupted-task")
            intent = next(Path(self.state_dir).glob("*.json"))
            old_key = json.loads(intent.read_text())["subject_key"]
            self.assertEqual(json.loads(intent.read_text())["status"], "in_flight")
            interrupt = False
            self.invoke_actual_client("--artifact-id", "new-task-after-interruption")
        tasks = self.continuation_work()["work"]
        old = next((task for task in tasks if task["id"] == "api:" + old_key), None)
        self.assertIsNotNone(old, "Interrupted predecessor intent was silently dropped")
        self.assertEqual(old["state"], "OPEN")
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        self.assertEqual(json.loads(intent.read_text())["status"], "in_flight")

    def test_history_write_failure_does_not_drop_failed_work_on_changed_request(self) -> None:
        opener, _ = self.transport(failure=True)
        writer = client.atomic_write_bytes
        writes = 0

        def fail_history(*args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 3:
                raise OSError("fixture:history write unavailable")
            return writer(*args, **kwargs)

        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "atomic_write_bytes", side_effect=fail_history):
            self.assertEqual(self.invoke_actual_client("--artifact-id", "failed-history-task"), 1)
        record = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
        old_key = record["subject_key"]
        self.assertEqual(record["status"], "failed")
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client("--artifact-id", "changed-after-history-failure")
        old = next((task for task in self.continuation_work()["work"] if task["id"] == "api:" + old_key), None)
        self.assertIsNotNone(old, "Failed predecessor was dropped after work persistence failed")
        self.assertEqual(old["state"], "OPEN")

    def test_failed_run_open_work_is_inherited_by_noop_successor(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            first = self.continuation_work()
            self.invoke_actual_client()
        second = self.continuation_work()
        self.assertEqual(second["previous_run"]["execution_id"], first["execution_id"])
        self.assertEqual(set(second["previous_run"]["open_work"]),
                         {task["id"] for task in first["work"] if task["state"] == "OPEN"})
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1)
        self.assertEqual(sum(request.get_method() == "GET" for request in requests), 4)
        self.assertEqual(len(list(Path(self.state_dir).glob("work-*.data"))), 2)

    def test_changed_request_keeps_previous_unrepaired_operation(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client("--artifact-id", "previous-task")
            first = self.continuation_work()
            old_api = next(task["id"] for task in first["work"] if task["id"].startswith("api:"))
            self.invoke_actual_client("--artifact-id", "different-task")
        tasks = self.continuation_work()["work"]
        self.assertEqual(next(task["state"] for task in tasks if task["id"] == old_api), "OPEN")
        self.assertEqual(sum(task["id"].startswith("api:") for task in tasks), 2)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)

    def test_open_repository_gap_closes_only_after_fresh_readback(self) -> None:
        opener, _ = self.transport()
        original = opener.open.side_effect
        broken = True

        def repository_gap(request, **kwargs):
            response = original(request, **kwargs)
            if broken and request.full_url.startswith("https://api.github.com/"):
                response.raw = b'{}'
            return response

        opener.open.side_effect = repository_gap
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            first = self.continuation_work()
            identifier = "repository:ingolf-lohmann/qik-vrt@main"
            self.assertEqual(next(task["state"] for task in first["work"] if task["id"] == identifier), "OPEN")
            broken = False
            self.invoke_actual_client("--artifact-id", "successor-subject")
        second = self.continuation_work()
        task = next(task for task in second["work"] if task["id"] == identifier)
        self.assertEqual(task["state"], "VERIFIED")
        self.assertTrue(task["evidence"])
        self.assertIn(identifier, second["previous_run"]["open_work"])

    def test_scoped_success_leaves_public_delivery_as_next_run_task(self) -> None:
        opener, _ = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        receipt = self.continuation_work()
        self.assertEqual(next(task["state"] for task in receipt["work"] if task["id"] == "delivery:raumzeitterminal.de"), "OPEN")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])
        self.assertNotIn("test-token", json.dumps(receipt))

    def test_corrupt_continuation_cannot_erase_previous_obligations_or_post(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            path = Path(self.state_dir) / "CONTINUATION.data"
            path.write_text("corrupt")
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1)
        self.assertEqual(path.read_text(), "corrupt")
        self.assertEqual(len(list(Path(self.state_dir).glob("work-*.data"))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
