#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2"
readonly ARCHIVE_SHA256="486a46afbb7ba798507190ffe02fea2dd726049af212e774537efac6afb210a6"
MODEL_DIR="${QIKVRT_AUDIO_MODEL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/transcribe-audio-offline/model-small}"

if [[ "${1:-}" == "--model-dir" ]]; then
  MODEL_DIR="${2:?missing value for --model-dir}"
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--model-dir DIR]" >&2
  exit 2
fi

for command in curl tar sha256sum install mktemp; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
archive="$temporary_dir/sherpa-onnx-whisper-small.tar.bz2"
extracted="$temporary_dir/extracted"
checksums="$temporary_dir/model.sha256"
mkdir -p "$extracted"
install -d -m 0700 "$MODEL_DIR"

cat > "$checksums" <<'EOF'
acad50b5c782696e91b55914cc5ab4f756f1532f76e22aa6fc615f39fb69a8ee  small-decoder.int8.onnx
4cbe7b22fa9026b843b60a68640c747de05bafb1a11b57edc0e66c232d9f33a9  small-encoder.int8.onnx
b34b360dbb493e781e479794586d661700670d65564001f23024971d1f2fa126  small-tokens.txt
EOF

echo "Downloading model archive only; no audio is transmitted." >&2
curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 --max-time 1800 \
  --output "$archive" "$MODEL_URL"
printf '%s  %s\n' "$ARCHIVE_SHA256" "$archive" | sha256sum -c -

tar --no-same-owner -xjf "$archive" -C "$extracted" --strip-components=1 \
  sherpa-onnx-whisper-small/small-decoder.int8.onnx \
  sherpa-onnx-whisper-small/small-encoder.int8.onnx \
  sherpa-onnx-whisper-small/small-tokens.txt

# Verify the extracted bytes before any persistent installation. The checksum
# file contains relative names, so sha256sum must execute inside the directory
# whose contents are being attested.
(
  cd "$extracted"
  sha256sum -c "$checksums"
)

install -m 0644 "$extracted/small-decoder.int8.onnx" "$MODEL_DIR/small-decoder.int8.onnx"
install -m 0644 "$extracted/small-encoder.int8.onnx" "$MODEL_DIR/small-encoder.int8.onnx"
install -m 0644 "$extracted/small-tokens.txt" "$MODEL_DIR/small-tokens.txt"

# Re-attest the persisted destination. Keeping both cd and sha256sum in the
# same subshell prevents pipeline process scope from silently changing cwd.
(
  cd "$MODEL_DIR"
  sha256sum -c "$checksums"
)

echo "Model installed at: $MODEL_DIR" >&2
