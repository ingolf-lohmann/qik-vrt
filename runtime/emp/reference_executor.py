"""Bounded EMP executor for an allowlisted, locally testable effect.

This is a reference executor, NOT an authorized GitHub writer. It atomically
writes a designated output file and independently reads it back. Only a
pre-authorized path under the designated root is permitted.
"""
import hashlib
import os
import tempfile
from pathlib import Path


def execute_file_effect(root: str, relative_path: str, payload: bytes,
                        *, authorized: bool, expected_sha256: str) -> dict:
    if not authorized:
        raise PermissionError("principal authorization required")
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("expected digest mismatch")
    base = Path(root).resolve(strict=True)
    target = (base / relative_path).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError("path outside authorized root")
    if target.exists() and target.is_symlink():
        raise ValueError("symlink target forbidden")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".emp-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
        dirfd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    observed = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"path": relative_path, "expected_sha256": expected_sha256,
            "observed_sha256": observed,
            "observed": observed == expected_sha256,
            "eap_verified": False, "effect_ack_done": False}
