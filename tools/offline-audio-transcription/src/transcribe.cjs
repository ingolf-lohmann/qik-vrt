#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const sherpa = require("sherpa-onnx-node");
const { mergeWithWordOverlap } = require("./merge.cjs");

process.umask(0o077);

const SAMPLE_RATE = 16000;
const MODEL_FILES = [
  "base-encoder.int8.onnx",
  "base-decoder.int8.onnx",
  "base-tokens.txt",
];

function usage() {
  return `Usage:
  transcribe-audio --input FILE --output-dir DIR [options]

Options:
  --language CODE       Whisper language code (default: de)
  --model-dir DIR       Directory containing the three model files
  --chunk-seconds N     Segment length below the 30 s engine limit (default: 28)
  --overlap-seconds N   Segment overlap (default: 1.5)
  --threads N           CPU threads (default: 4)
  --force               Replace existing output files
  --help                Show this help
`;
}

function parseArgs(argv) {
  const options = {
    language: "de",
    chunkSeconds: 28,
    overlapSeconds: 1.5,
    threads: 4,
    force: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help") options.help = true;
    else if (arg === "--force") options.force = true;
    else if (arg === "--input") options.input = argv[++index];
    else if (arg === "--output-dir") options.outputDir = argv[++index];
    else if (arg === "--language") options.language = argv[++index];
    else if (arg === "--model-dir") options.modelDir = argv[++index];
    else if (arg === "--chunk-seconds") options.chunkSeconds = Number(argv[++index]);
    else if (arg === "--overlap-seconds") options.overlapSeconds = Number(argv[++index]);
    else if (arg === "--threads") options.threads = Number(argv[++index]);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function sha256(file) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(file));
  return hash.digest("hex");
}

function firstLine(command, args) {
  return execFileSync(command, args, { encoding: "utf8" }).split(/\r?\n/u)[0];
}

function safeStem(filename) {
  const stem = path.parse(filename).name.normalize("NFKC");
  const safe = stem.replace(/[^\p{L}\p{N}._-]+/gu, "_").replace(/^_+|_+$/gu, "");
  return safe || "audio";
}

function loadManifest(toolRoot) {
  const manifestPath = path.join(toolRoot, "models", "whisper-base-int8", "MODEL.json");
  return { manifestPath, manifest: JSON.parse(fs.readFileSync(manifestPath, "utf8")) };
}

function verifyModel(modelDir, manifest) {
  const expected = new Map(manifest.files.map((item) => [item.name, item]));
  return MODEL_FILES.map((name) => {
    const file = path.join(modelDir, name);
    if (!fs.statSync(file).isFile()) throw new Error(`Model file is not regular: ${name}`);
    const bytes = fs.statSync(file).size;
    const digest = sha256(file);
    const record = expected.get(name);
    if (!record) throw new Error(`Model manifest has no entry for ${name}`);
    if (record.bytes !== bytes || record.sha256 !== digest) {
      throw new Error(`Model integrity check failed for ${name}`);
    }
    return { name, bytes, sha256: digest };
  });
}

function writeJson(file, value) {
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    process.stdout.write(usage());
    return;
  }
  if (!options.input || !options.outputDir) throw new Error("--input and --output-dir are required");
  if (!(options.chunkSeconds > 0 && options.chunkSeconds < 30)) {
    throw new Error("--chunk-seconds must be greater than 0 and less than 30");
  }
  if (!(options.overlapSeconds >= 0 && options.overlapSeconds < options.chunkSeconds)) {
    throw new Error("--overlap-seconds must be non-negative and smaller than the chunk length");
  }
  if (!Number.isInteger(options.threads) || options.threads < 1) {
    throw new Error("--threads must be a positive integer");
  }

  const toolRoot = path.resolve(__dirname, "..");
  const dataHome = process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
  const modelDir = path.resolve(
    options.modelDir || process.env.QIKVRT_AUDIO_MODEL_DIR || path.join(dataHome, "transcribe-audio-offline", "model"),
  );
  const input = path.resolve(options.input);
  const outputDir = path.resolve(options.outputDir);
  if (!fs.statSync(input).isFile()) throw new Error("Input is not a regular file");

  const sourceHashBefore = sha256(input);
  const { manifestPath, manifest } = loadManifest(toolRoot);
  const verifiedModel = verifyModel(modelDir, manifest);
  const durationSeconds = Number(firstLine("ffprobe", [
    "-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", input,
  ]));
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) throw new Error("Could not determine audio duration");

  fs.mkdirSync(outputDir, { recursive: true, mode: 0o700 });
  const stem = safeStem(path.basename(input));
  const textPath = path.join(outputDir, `${stem}.transcript.txt`);
  const jsonPath = path.join(outputDir, `${stem}.transcript.json`);
  const provenancePath = path.join(outputDir, `${stem}.provenance.json`);
  for (const output of [textPath, jsonPath, provenancePath]) {
    if (!options.force && fs.existsSync(output)) throw new Error(`Output exists; use --force: ${path.basename(output)}`);
  }

  const temporaryDir = fs.mkdtempSync(path.join(os.tmpdir(), "qikvrt-transcribe-"));
  const rawPath = path.join(temporaryDir, "audio.f32");
  try {
    execFileSync("ffmpeg", [
      "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", input,
      "-ac", "1", "-ar", String(SAMPLE_RATE), "-f", "f32le", rawPath,
    ], { stdio: "inherit" });

    const recognizer = new sherpa.OfflineRecognizer({
      featConfig: { sampleRate: SAMPLE_RATE, featureDim: 80 },
      modelConfig: {
        whisper: {
          encoder: path.join(modelDir, "base-encoder.int8.onnx"),
          decoder: path.join(modelDir, "base-decoder.int8.onnx"),
          tailPaddings: 1000,
          language: options.language,
        },
        tokens: path.join(modelDir, "base-tokens.txt"),
        numThreads: options.threads,
        provider: "cpu",
      },
    });

    const bytes = fs.readFileSync(rawPath);
    const samples = new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4);
    const chunkSamples = Math.floor(options.chunkSeconds * SAMPLE_RATE);
    const stepSamples = Math.floor((options.chunkSeconds - options.overlapSeconds) * SAMPLE_RATE);
    const segments = [];
    let mergedText = "";

    for (let start = 0, index = 0; start < samples.length; start += stepSamples, index += 1) {
      const end = Math.min(samples.length, start + chunkSamples);
      const chunk = samples.slice(start, end);
      const stream = recognizer.createStream();
      stream.acceptWaveform({ samples: chunk, sampleRate: SAMPLE_RATE });
      recognizer.decode(stream);
      const result = recognizer.getResult(stream);
      const text = result.text.trim();
      segments.push({
        index,
        startSeconds: start / SAMPLE_RATE,
        endSeconds: end / SAMPLE_RATE,
        text,
      });
      mergedText = mergeWithWordOverlap(mergedText, text);
      if (end === samples.length) break;
    }

    if (!mergedText.trim()) throw new Error("Transcription produced empty text");
    const transcript = {
      schemaVersion: "1.0.0",
      generatedAt: new Date().toISOString(),
      sourceFilename: path.basename(input),
      language: options.language,
      durationSeconds,
      text: mergedText.trim(),
      segments,
      note: "Segment times are processing windows, not word-level timestamps.",
    };
    fs.writeFileSync(textPath, `${transcript.text}\n`, { mode: 0o600 });
    writeJson(jsonPath, transcript);

    const sourceHashAfter = sha256(input);
    if (sourceHashAfter !== sourceHashBefore) throw new Error("Input changed during transcription");
    const packageVersion = JSON.parse(fs.readFileSync(path.join(toolRoot, "package.json"), "utf8")).version;
    const provenance = {
      schemaVersion: "1.0.0",
      generatedAt: transcript.generatedAt,
      privacyMode: "local-only; no audio or transcript sent to a network service",
      input: {
        filename: path.basename(input),
        bytes: fs.statSync(input).size,
        durationSeconds,
        sha256: sourceHashBefore,
      },
      engine: {
        tool: "@qik-vrt/offline-audio-transcription",
        version: packageVersion,
        node: process.version,
        sherpaOnnxNode: "1.13.4",
        ffmpeg: firstLine("ffmpeg", ["-version"]),
      },
      model: {
        id: manifest.id,
        manifest: path.relative(toolRoot, manifestPath),
        files: verifiedModel,
      },
      parameters: {
        language: options.language,
        sampleRate: SAMPLE_RATE,
        chunkSeconds: options.chunkSeconds,
        overlapSeconds: options.overlapSeconds,
        threads: options.threads,
      },
      outputs: [textPath, jsonPath].map((file) => ({
        filename: path.basename(file),
        bytes: fs.statSync(file).size,
        sha256: sha256(file),
      })),
    };
    writeJson(provenancePath, provenance);

    process.stdout.write(`${JSON.stringify({
      transcript: textPath,
      structuredTranscript: jsonPath,
      provenance: provenancePath,
    })}\n`);
  } finally {
    fs.rmSync(temporaryDir, { recursive: true, force: true });
  }
}

try {
  main();
} catch (error) {
  process.stderr.write(`transcribe-audio: ${error.message}\n`);
  process.exitCode = 1;
}
