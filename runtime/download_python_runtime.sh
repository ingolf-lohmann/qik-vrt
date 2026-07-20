#!/usr/bin/env bash
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
# Platform-general dependency adapter: Unix/macOS runtime resolver continue path.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
LOG_FILE="$LOG_DIR/qikvrt_last_run.jsonl"
mkdir -p "$LOG_DIR"
echo '{"event":"dependency_download_consent_required","dependency_id":"python_runtime","status":"CONTINUE","platform_adapter":"unix_macos_shell","continue_path":"USE_SYSTEM_PACKAGE_MANAGER_OR_BUNDLE_PYTHON_RUNTIME","license_area":"third_party_python_runtime"}' >> "$LOG_FILE"
echo "Python runtime is not bundled for this Unix/macOS adapter."
echo "Continue path: install Python 3 or provide runtime/python/linux/python3 or runtime/python/macos/python3."
exit 20
