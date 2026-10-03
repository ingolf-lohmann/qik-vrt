#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Machine-readable, fail-closed JSONL logging for QIK-VRT launchers."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import secrets
import stat
import sys
import threading
import time
import traceback
from typing import Any, Callable, TypeVar

if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    import msvcrt
else:
    import fcntl

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "qikvrt_last_run.jsonl"
LOG_FILE = DEFAULT_LOG_FILE
MAX_POINTER_LOG_BYTES = 16 * 1024 * 1024

_WRITE_LOCK = threading.Lock()
_T = TypeVar("_T")


def _windows_private_open(path: pathlib.Path, flags: int, *, protect_owner_dacl: bool = True) -> int:
    """Open the actual file, reject reparse points and protect its owner DACL."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
        wintypes.LPVOID, wintypes.DWORD]
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [wintypes.LPVOID]
    kernel.LocalFree.restype = wintypes.LPVOID
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), wintypes.LPVOID]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    security.GetSecurityDescriptorDacl.argtypes = [wintypes.LPVOID,
        ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.BOOL)]
    security.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    security.SetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
        wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID]
    security.SetSecurityInfo.restype = wintypes.DWORD
    access = 0x00040000 if protect_owner_dacl else 0
    access |= 0x40000000 if flags & os.O_WRONLY else 0x80000000
    disposition = 1 if flags & os.O_EXCL else 4 if flags & os.O_CREAT else 3
    # Public immutable input reads deny concurrent write/delete and do not
    # mutate source permissions. Runtime logs retain their private DACL contract.
    share = 7 if protect_owner_dacl else 1
    handle = kernel.CreateFileW(str(path), access, share, None, disposition, 0x00200080, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    descriptor = None
    try:
        attributes = (wintypes.DWORD * 2)()
        if not kernel.GetFileInformationByHandleEx(handle, 9, attributes, ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes[0] & 0x400:
            raise OSError(f"runtime file must not be a reparse point: {path}")
        descriptor = msvcrt.open_osfhandle(handle, (flags & os.O_APPEND) | os.O_BINARY | os.O_NOINHERIT)
        handle = None  # The CRT descriptor now owns the native handle.
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise OSError(f"runtime file is not a regular unaliased file: {path}")
        if not protect_owner_dacl:
            return descriptor
        security_descriptor = wintypes.LPVOID()
        if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                "D:P(A;;FA;;;OW)", 1, ctypes.byref(security_descriptor), None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), wintypes.LPVOID()
            if not security.GetSecurityDescriptorDacl(security_descriptor, ctypes.byref(present),
                    ctypes.byref(dacl), ctypes.byref(defaulted)) or not present.value or not dacl.value:
                raise OSError("runtime owner DACL must be present and non-null")
            result = security.SetSecurityInfo(msvcrt.get_osfhandle(descriptor), 1, 0x80000004,
                None, None, dacl, None)
            if result:
                raise ctypes.WinError(result)
        finally:
            kernel.LocalFree(security_descriptor)
        return descriptor
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        raise
    finally:
        if handle is not None:
            kernel.CloseHandle(handle)


def _lock_log(descriptor: int, *, shared: bool = False, release: bool = False) -> None:
    if os.name != "nt":
        fcntl.flock(descriptor, fcntl.LOCK_UN if release else fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        return
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        mode = msvcrt.LK_UNLCK if release else msvcrt.LK_RLCK if shared else msvcrt.LK_LOCK
        msvcrt.locking(descriptor, mode, 1)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)


def utc_now() -> str:
    """Return a stable, second-resolution UTC timestamp."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def json_safe_path(path: str | pathlib.Path) -> str:
    """Return a platform-independent path representation for JSON evidence."""
    return str(path).replace("\\", "/")


def _json_safe(value: Any) -> Any:
    if isinstance(value, pathlib.Path):
        return json_safe_path(value)
    if isinstance(value, str):
        # ``run_bounded`` deliberately uses surrogateescape so arbitrary POSIX
        # child-output bytes remain reversible for machine callers.  JSONL must
        # still be valid UTF-8, therefore replace only unencodable surrogate
        # code points before serialization instead of letting logging fail
        # after the child process has already run.
        return value.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if value is None or isinstance(value, (int, bool)):
        return value
    return str(value)


def ensure_log_dir() -> pathlib.Path:
    """Create and return the volatile runtime log directory."""
    if LOG_DIR.is_symlink() or (os.name == "nt" and LOG_DIR.is_junction()):
        raise OSError(f"runtime log directory must not be a symlink: {LOG_DIR}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_DIR.is_dir() or LOG_DIR.is_symlink() or (os.name == "nt" and LOG_DIR.is_junction()):
        raise OSError(f"runtime log directory is not a regular directory: {LOG_DIR}")
    return LOG_DIR


def _open_log(flags: int) -> int:
    """Open the fixed log without following a substituted final symlink."""
    ensure_log_dir()
    if os.name == "nt":
        return _windows_private_open(LOG_FILE, flags)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(LOG_FILE, flags | nofollow, 0o600)
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode) or file_status.st_nlink != 1:
            raise OSError(f"runtime log is not a regular file: {LOG_FILE}")
        os.fchmod(descriptor, 0o600)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("runtime log write made no forward progress")
        view = view[written:]


def _read_current_log_bounded() -> bytes:
    """Read the completed run log without following substitutions."""
    descriptor = _open_log(os.O_RDONLY)
    try:
        _lock_log(descriptor, shared=True)
        before = os.fstat(descriptor)
        if before.st_size > MAX_POINTER_LOG_BYTES:
            raise OSError("runtime log exceeds the latest-pointer size bound")
        chunks: list[bytes] = []
        remaining = MAX_POINTER_LOG_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(data) > MAX_POINTER_LOG_BYTES or len(data) != before.st_size:
            raise OSError("runtime log changed size while building the latest pointer")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise OSError("runtime log changed while building the latest pointer")
        return data
    finally:
        _lock_log(descriptor, release=True)
        os.close(descriptor)


def _select_unique_run_log() -> pathlib.Path:
    global LOG_FILE
    production_default = LOG_FILE == DEFAULT_LOG_FILE
    prior_generated = (
        LOG_FILE.parent == LOG_DIR and LOG_FILE.name.startswith("qikvrt-run-")
    )
    if production_default or prior_generated:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        LOG_FILE = LOG_DIR / (
            f"qikvrt-run-{stamp}-{os.getpid()}-{secrets.token_hex(6)}.jsonl"
        )
    return LOG_FILE


def _write_latest_pointer(status: str, exit_code: int) -> None:
    pointer = LOG_DIR / "qikvrt_last_run.json"
    if pointer.is_symlink():
        raise OSError(f"runtime log pointer must not be a symlink: {pointer}")
    log_bytes = _read_current_log_bounded()
    payload = {
        "schema": "qikvrt_latest_run_pointer_v1",
        "logfile": json_safe_path(LOG_FILE),
        "sha256": hashlib.sha256(log_bytes).hexdigest(),
        "bytes": len(log_bytes),
        "status": status,
        "exit_code": int(exit_code),
        "finished_utc": utc_now(),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    temporary = pointer.with_name(
        f".{pointer.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = (_windows_private_open(temporary, flags) if os.name == "nt"
        else os.open(temporary, flags, 0o600))
    try:
        _write_all(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        if os.name == "nt":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            kernel.MoveFileExW.restype = wintypes.BOOL
            if not kernel.MoveFileExW(str(temporary), str(pointer), 0x9):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.replace(temporary, pointer)
            directory_descriptor = os.open(LOG_DIR, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_event(event: str, **fields: Any) -> dict[str, Any]:
    """Append exactly one valid JSON object to the runtime JSONL log."""
    if not event or not isinstance(event, str):
        raise ValueError("event must be a non-empty string")
    ensure_log_dir()
    payload = {
        "timestamp": utc_now(),
        "event": event,
        **{key: _json_safe(value) for key, value in fields.items()},
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    with _WRITE_LOCK:
        descriptor = _open_log(os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            _lock_log(descriptor)
            _write_all(descriptor, encoded)
            os.fsync(descriptor)
        finally:
            _lock_log(descriptor, release=True)
            os.close(descriptor)
    return payload


def reset_log(launcher: str) -> pathlib.Path:
    """Start a unique per-run log without truncating another process's evidence."""
    ensure_log_dir()
    with _WRITE_LOCK:
        _select_unique_run_log()
        descriptor = _open_log(os.O_WRONLY | os.O_CREAT)
        try:
            _lock_log(descriptor)
            os.ftruncate(descriptor, 0)
            os.fsync(descriptor)
        finally:
            _lock_log(descriptor, release=True)
            os.close(descriptor)
    write_event(
        "run_start",
        launcher=launcher,
        platform=sys.platform,
        logfile=json_safe_path(LOG_FILE),
    )
    return LOG_FILE


def log_command_start(command: str | list[str]) -> dict[str, Any]:
    """Record a command before it is invoked."""
    return write_event("command_start", command=command)


def log_stream(stream_name: str, command: str, text: str) -> dict[str, Any]:
    """Record captured target output without interpreting it as success."""
    if stream_name not in {"stdout", "stderr"}:
        raise ValueError("stream_name must be stdout or stderr")
    return write_event(stream_name, command=command, text=text)


def log_check_result(
    check_name: str,
    status: str,
    exit_code: int = 0,
    duration_ms: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Record the result of an actually executed check."""
    payload: dict[str, Any] = {
        "check_name": check_name,
        "status": status,
        "exit_code": int(exit_code),
    }
    if duration_ms is not None:
        payload["duration_ms"] = int(duration_ms)
    if error:
        payload["error"] = str(error)
    return write_event("check_result", **payload)


def log_repair_hint(
    error_class: str,
    hint: str,
    severity: str = "CONTINUE",
    continue_path: str = "INSPECT_LOG_AND_REPAIR_NEXT_ERROR",
) -> dict[str, Any]:
    """Record a machine-readable recovery path for a non-PASS result."""
    return write_event(
        "repair_hint",
        error_class=error_class,
        hint=hint,
        severity=severity,
        continue_path=continue_path,
    )


def finish(
    exit_code: int,
    status: str | None = None,
    continue_path: str | None = None,
    error_class: str | None = None,
    repair_hint: str | None = None,
) -> int:
    """Write the canonical run_end event and preserve the supplied exit code."""
    code = int(exit_code)
    if status is None:
        status = "PASS" if code == 0 else ("CONTINUE" if code == 20 else "BLOCK")
    if code != 0 and status in {"DONE", "DONE_BY_PYTHON_LAUNCHER", "PASS"}:
        status = "BLOCK"
    payload = {
        "exit_code": code,
        "status": status,
        "error_class": "NONE" if code == 0 else (error_class or "NONZERO_EXIT"),
        "continue_path": "NONE" if code == 0 else (
            continue_path or "INSPECT_LOG_AND_REPAIR_NEXT_ERROR"
        ),
        "repair_hint": "NONE" if code == 0 else (
            repair_hint or "Inspect the preceding result and repair its underlying cause."
        ),
        "logfile": json_safe_path(LOG_FILE),
    }
    write_event("run_end", **payload)
    _write_latest_pointer(status, code)
    return code


def run_logged(label: str, callable_obj: Callable[[], _T]) -> _T:
    """Execute a callable and persist duration and exception evidence."""
    start = time.monotonic()
    log_command_start(label)
    try:
        result = callable_obj()
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        log_check_result(label, "BLOCK", 1, duration_ms, str(exc))
        log_stream("stderr", label, traceback.format_exc())
        log_repair_hint(
            "UNHANDLED_RUNTIME_EXCEPTION",
            f"Repair the failing command: {label}",
            "BLOCK",
            "REPAIR_COMMAND_AND_RERUN",
        )
        raise
    log_check_result(label, "PASS", 0, int((time.monotonic() - start) * 1000))
    return result
