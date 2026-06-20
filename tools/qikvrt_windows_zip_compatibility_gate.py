#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate Windows ZIP extraction compatibility."""
from __future__ import annotations
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "canonical" / "WINDOWS_ZIP_EXTRACTION_COMPATIBILITY_GATE_V36.json"

def validate_repo_paths():
    """Validate repo-relative paths are conservative before zipping under QV36."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    max_zip_path = int(config["max_internal_zip_path_length"])
    max_file_name = int(config["max_filename_length"])
    root_name = config["top_level_directory_required"]
    for path in ROOT.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
            rel = path.relative_to(ROOT).as_posix()
            arc = root_name + "/" + rel
            assert len(arc) <= max_zip_path, f"ZIP path too long: {len(arc)} {arc}"
            assert len(path.name) <= max_file_name, f"filename too long: {len(path.name)} {path.name}"
            assert not rel.startswith("/") and ".." not in pathlib.PurePosixPath(rel).parts, "unsafe relative path: " + rel

def validate_zip(zip_path):
    """Validate actual ZIP entries."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    max_zip_path = int(config["max_internal_zip_path_length"])
    root_name = config["top_level_directory_required"]
    with zipfile.ZipFile(zip_path, "r") as z:
        bad = z.testzip()
        assert bad is None, "zip integrity failure: " + str(bad)
        names = [i.filename for i in z.infolist()]
    assert names, "zip empty"
    assert len(names) == len(set(names)), "duplicate zip entries"
    for name in names:
        assert name.startswith(root_name + "/"), "wrong top-level directory: " + name
        assert len(name) <= max_zip_path, f"ZIP path too long: {len(name)} {name}"
        parts = pathlib.PurePosixPath(name).parts
        assert ".." not in parts, "path traversal entry: " + name
        assert not name.startswith("/") and ":" not in parts[0], "absolute or drive path: " + name
    return True

def main(argv=None):
    """Run gate."""
    argv = argv or []
    validate_repo_paths()
    if argv:
        validate_zip(pathlib.Path(argv[0]))
    print("PASS Windows ZIP extraction compatibility gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
