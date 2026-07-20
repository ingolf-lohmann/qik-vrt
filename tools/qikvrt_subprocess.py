#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Run a child process with hard time and captured-output bounds."""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class BoundedProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    output_limit_exceeded: bool


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == "posix":
        # ``start_new_session=True`` makes the child's PID its process-group
        # id.  The group can remain alive after the direct child exits (for
        # example when a grandchild inherited stdout/stderr), so do not return
        # early merely because ``process.poll()`` is no longer ``None``.
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except OSError:
            pass
    if process.poll() is None:
        with contextlib.suppress(OSError):
            process.kill()


def run_bounded(
    command: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 180,
    max_output_bytes: int = 1_048_576,
) -> BoundedProcessResult:
    """Capture at most ``max_output_bytes`` from each stream and fail closed."""
    if not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("command must contain non-empty string arguments")
    if not 0 < timeout <= 3600:
        raise ValueError("timeout must be between 0 and 3600 seconds")
    if not 1024 <= max_output_bytes <= 16 * 1024 * 1024:
        raise ValueError("max_output_bytes must be between 1024 and 16777216")

    process = subprocess.Popen(
        list(command),
        cwd=None if cwd is None else Path(cwd),
        env=None if env is None else dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )
    assert process.stdout is not None and process.stderr is not None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limit_exceeded = threading.Event()
    termination_lock = threading.Lock()
    reader_errors: list[str] = []

    def terminate_once() -> None:
        with termination_lock:
            _terminate_process_tree(process)

    def reader(name: str, stream: object) -> None:
        readable = stream
        try:
            while True:
                chunk = readable.read(65536)  # type: ignore[attr-defined]
                if not chunk:
                    break
                buffer = buffers[name]
                remaining = max_output_bytes - len(buffer)
                if remaining > 0:
                    buffer.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    limit_exceeded.set()
                    terminate_once()
        except OSError as exc:
            reader_errors.append(f"{name}: {exc}")
            terminate_once()

    threads = [
        threading.Thread(target=reader, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=reader, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_once()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            terminate_once()
            process.wait(timeout=5)
    # A direct child may exit after spawning descendants that keep inherited
    # pipes alive. Give readers a brief drain window, then clear that remaining
    # process group rather than waiting indefinitely on pipe EOF.
    for thread in threads:
        thread.join(timeout=0.1)
    if any(thread.is_alive() for thread in threads):
        terminate_once()
    for thread in threads:
        thread.join(timeout=5)
    if any(thread.is_alive() for thread in threads):
        terminate_once()
        for thread in threads:
            thread.join(timeout=5)
    if any(thread.is_alive() for thread in threads):
        # Closing the local pipe descriptors is the last bounded unblock path;
        # never leave daemon readers and inherited pipes silently running.
        with contextlib.suppress(OSError):
            process.stdout.close()
        with contextlib.suppress(OSError):
            process.stderr.close()
        for thread in threads:
            thread.join(timeout=1)
        raise RuntimeError("bounded subprocess output reader did not terminate")
    process.stdout.close()
    process.stderr.close()
    if reader_errors:
        raise RuntimeError("bounded subprocess output read failed: " + "; ".join(reader_errors))

    return BoundedProcessResult(
        command=tuple(command),
        returncode=int(process.returncode if process.returncode is not None else 1),
        # ``surrogateescape`` keeps arbitrary POSIX filename bytes reversible
        # for callers such as the integrity generator while remaining ordinary
        # text for normal UTF-8 command output.
        stdout=bytes(buffers["stdout"]).decode("utf-8", errors="surrogateescape"),
        stderr=bytes(buffers["stderr"]).decode("utf-8", errors="surrogateescape"),
        timed_out=timed_out,
        output_limit_exceeded=limit_exceeded.is_set(),
    )
