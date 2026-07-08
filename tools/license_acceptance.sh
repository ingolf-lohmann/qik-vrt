#!/bin/sh
# QIKVRT Artifact Header
# Deutsch: Verpflichtende Laufzeit-Akzeptanz von Urheber-, Rechte- und Lizenzbedingungen vor jeder weiteren Aktivitaet.
# English: Mandatory runtime acceptance of authorship, rights and license terms before any further activity.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
set -eu
REPO_ROOT="${1:-$(pwd)}"
CONFIG_DIR="$REPO_ROOT/qikvrt/config"
LEDGER_DIR="$REPO_ROOT/qikvrt/ledger"
ACCEPTED_FILE="$CONFIG_DIR/LICENSE_ACCEPTED.json"
LEDGER_FILE="$LEDGER_DIR/LICENSE_RUNTIME_ACCEPTANCE.jsonl"
mkdir -p "$CONFIG_DIR" "$LEDGER_DIR"
if [ -f "$ACCEPTED_FILE" ] && grep -q '"accepted"[[:space:]]*:[[:space:]]*true' "$ACCEPTED_FILE"; then
  printf '%s\t%s\t%s\n' 'LICENSE_RUNTIME_ACCEPTANCE' 'PASS' 'previous acceptance persisted'
  exit 0
fi
persist_acceptance(){
  TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  cat > "$ACCEPTED_FILE" <<EOF
{"version":"2.13.4","accepted":true,"accepted_utc":"$TS","source":"$1","author":"Ingolf Lohmann","rights_holder":"Ingolf Lohmann or a legal entity designated by him","software_license":"Apache-2.0","non_software_license":"CC BY-NC-ND 4.0 unless otherwise stated","gate":"QIKVRT_LICENSE_AUTHORSHIP_RIGHTS_ACCEPTANCE_BEFORE_ACTIVITY"}
EOF
  cat "$ACCEPTED_FILE" >> "$LEDGER_FILE"
  printf '\n' >> "$LEDGER_FILE"
  printf '%s\t%s\t%s\n' 'LICENSE_RUNTIME_ACCEPTANCE' 'PASS' 'accepted and persisted before further QIKVRT activity'
}
if [ "${QIKVRT_ACCEPT_LICENSE:-}" = "1" ]; then persist_acceptance 'environment:QIKVRT_ACCEPT_LICENSE'; exit 0; fi
printf '%s\n' 'QIKVRT LICENSE / AUTHORSHIP / RIGHTS ACCEPTANCE'
printf '%s\n' 'DE: Vor jeder weiteren QIKVRT-Aktivitaet muessen Urheber-, Rechte- und Lizenzbedingungen akzeptiert werden.'
printf '%s\n' 'EN: Before any further QIKVRT activity, authorship, rights and license terms must be accepted.'
printf '%s\n' 'Urheber / Author: Ingolf Lohmann'
printf '%s\n' 'Rechteinhaber / Rights holder: Ingolf Lohmann or a legal entity designated by him'
printf '%s\n' 'Software license: Apache-2.0'
printf '%s\n' 'Non-software/docs license: CC BY-NC-ND 4.0 unless otherwise stated'
printf '%s' 'Akzeptieren? Type JA or YES to continue: '
read ans
case "$(printf '%s' "$ans" | tr '[:lower:]' '[:upper:]')" in
  JA|J|YES|Y|ACCEPT) persist_acceptance 'interactive'; exit 0 ;;
  *) printf '%s\t%s\t%s\n' 'LICENSE_RUNTIME_ACCEPTANCE' 'BLOCK' 'not accepted; no further QIKVRT activity allowed'; exit 41 ;;
esac
