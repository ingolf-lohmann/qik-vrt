"use strict";
// SPDX-License-Identifier: MIT
// Contribution: Claude (Anthropic), QIK-VRT Mirror node.

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const toolRoot = path.resolve(__dirname, "..");
const pinned = [
  { model: "base", manifestDir: "whisper-base-int8", installer: "install-model.sh" },
  { model: "small", manifestDir: "whisper-small-int8", installer: "install-model-small.sh" },
];

for (const { model, manifestDir, installer } of pinned) {
  test(`${model}: installer pins exactly the manifest archive and files`, () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(toolRoot, "models", manifestDir, "MODEL.json"), "utf8"));
    const script = fs.readFileSync(path.join(toolRoot, "scripts", installer), "utf8");
    assert.match(script, new RegExp(`readonly MODEL_URL="${manifest.source.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`));
    assert.match(script, new RegExp(`readonly ARCHIVE_SHA256="${manifest.archiveSha256}"`));
    const heredoc = script.split("<<'EOF'\n")[1].split("\nEOF\n")[0].trim().split("\n");
    assert.deepEqual(
      heredoc.map((line) => line.split(/\s+/u)).sort((a, b) => a[1].localeCompare(b[1])),
      manifest.files.map((file) => [file.sha256, file.name]).sort((a, b) => a[1].localeCompare(b[1])),
    );
    for (const file of manifest.files) {
      assert.ok(file.name.startsWith(`${model}-`), `${file.name} must carry the ${model} prefix`);
      assert.ok(Number.isInteger(file.bytes) && file.bytes > 0);
    }
  });

  test(`${model}: installer verifies extracted bytes before and after installation`, () => {
    const value = fs.readFileSync(path.join(toolRoot, "scripts", installer), "utf8");
    const extractedCheck = value.indexOf('cd "$extracted"');
    const persistentInstall = value.indexOf(`install -m 0644 "$extracted/${model}-decoder.int8.onnx"`);
    const destinationCheck = value.indexOf('cd "$MODEL_DIR"');
    assert.ok(extractedCheck >= 0 && persistentInstall > extractedCheck && destinationCheck > persistentInstall);
    assert.doesNotMatch(value, /\)\s*\|\s*sha256sum\s+-c/u);
  });
}

test("transcriber selects only the two pinned models and keeps base as default", () => {
  const source = fs.readFileSync(path.join(toolRoot, "src", "transcribe.cjs"), "utf8");
  assert.match(source, /base: Object\.freeze\(\{ manifestDir: "whisper-base-int8", prefix: "base", defaultDir: "model" \}\)/u);
  assert.match(source, /small: Object\.freeze\(\{ manifestDir: "whisper-small-int8", prefix: "small", defaultDir: "model-small" \}\)/u);
  assert.match(source, /model: "base",/u);
  assert.match(source, /--model must be base or small/u);
  assert.doesNotMatch(source, /"base-(encoder|decoder)\.int8\.onnx"/u, "model file names must come from the selected model");
});
