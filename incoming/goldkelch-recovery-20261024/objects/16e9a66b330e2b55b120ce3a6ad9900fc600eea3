#!/bin/sh
# QIKVRT Artifact Header
# Deutsch: Einheitlicher POSIX-Einstiegspunkt fuer Setup, Test, Deploy und Seed-Registrierung.
# English: Unified POSIX entry point for setup, test, deploy and seed registration.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODE="${1:-acceptance}"
finish(){
  code="$1"
  printf '\nQIKVRT_SH_EXIT=%s\n' "$code"
  printf '%s\n' 'Result logs:'
  printf '%s\n' '  qikvrt/runtime/deploy/deploy_result.tsv'
  exit "$code"
}
case "$MODE" in help|-h|--help)
  printf '%s\n' 'Usage: ./QIKVRT.sh [setup|register|deploy|acceptance|test]'
  exit 2;;
esac
# Mandatory first gate: authorship / rights / license acceptance.
sh "$ROOT/tools/license_acceptance.sh" "$ROOT" || finish $?
case "$MODE" in
  setup) sh "$ROOT/tools/setup_repository.sh" "$ROOT"; finish $? ;;
  register) sh "$ROOT/tools/register_with_seed.sh" "$ROOT"; finish $? ;;
  deploy)
    # POSIX parity: create/persist GUID and GitHub target before deployment.
    sh "$ROOT/tools/setup_repository.sh" "$ROOT" || finish $?
    if [ "${QIKVRT_DRY_RUN:-}" != "1" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
      printf '%s\n' 'GitHub token is required for git push only. It will be used for this process only and will not be persisted; release creation is done by target GitHub Actions.'
      printf '%s' 'GitHub token: '
      stty -echo 2>/dev/null || true
      read tok || tok=''
      stty echo 2>/dev/null || true
      printf '\n'
      GITHUB_TOKEN="$tok"; export GITHUB_TOKEN
    fi
    sh "$ROOT/tools/gh_deploy.sh" "$ROOT"; finish $? ;;
  acceptance|test) make -C "$ROOT" test; finish $? ;;
  *) printf 'Unknown QIKVRT mode: %s\n' "$MODE"; finish 2 ;;
esac
