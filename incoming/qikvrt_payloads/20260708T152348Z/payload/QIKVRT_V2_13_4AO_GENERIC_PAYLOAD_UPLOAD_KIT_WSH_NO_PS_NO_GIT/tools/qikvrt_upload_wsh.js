// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 Ingolf Lohmann.
// QIK-VRT generic payload uploader for Windows Script Host / JScript.
// No PowerShell. No Git. No embedded token.

var VERSION = "QIKVRT_V2_13_4AO";
var fso = new ActiveXObject("Scripting.FileSystemObject");
var shell = new ActiveXObject("WScript.Shell");
var root = fso.GetParentFolderName(WScript.ScriptFullName);
root = fso.GetParentFolderName(root);

function out(s) { WScript.StdOut.WriteLine(s); }
function write(s) { WScript.StdOut.Write(s); }
function err(s) { WScript.StdErr.WriteLine(s); }
function trim(s) { return String(s).replace(/^\s+|\s+$/g, ""); }
function up(s) { return trim(s).toUpperCase(); }
function yes(s) { var v = up(s); return v === "JA" || v === "J" || v === "YES" || v === "Y"; }
function readLine(promptText) { write(promptText); return WScript.StdIn.ReadLine(); }
function pad2(n) { return (n < 10 ? "0" : "") + n; }
function timestampUTC() {
  var d = new Date();
  return d.getUTCFullYear() + pad2(d.getUTCMonth()+1) + pad2(d.getUTCDate()) + "T" + pad2(d.getUTCHours()) + pad2(d.getUTCMinutes()) + pad2(d.getUTCSeconds()) + "Z";
}
function ensureFolder(path) { if (!fso.FolderExists(path)) { fso.CreateFolder(path); } }
function ensureFolderDeep(path) {
  if (fso.FolderExists(path)) return;
  var parent = fso.GetParentFolderName(path);
  if (parent && !fso.FolderExists(parent)) ensureFolderDeep(parent);
  if (!fso.FolderExists(path)) fso.CreateFolder(path);
}
function relPath(abs, base) {
  var a = fso.GetAbsolutePathName(abs);
  var b = fso.GetAbsolutePathName(base);
  if (a.toLowerCase().indexOf(b.toLowerCase()) === 0) {
    a = a.substring(b.length);
    if (a.charAt(0) === "\\" || a.charAt(0) === "/") a = a.substring(1);
  }
  return a.replace(/\\/g, "/");
}
function quoteCmdPath(p) { return '"' + String(p).replace(/"/g, '""') + '"'; }
function execCapture(cmd) {
  var e = shell.Exec(cmd);
  var stdout = "";
  var stderr = "";
  while (e.Status === 0) { WScript.Sleep(20); }
  if (!e.StdOut.AtEndOfStream) stdout = e.StdOut.ReadAll();
  if (!e.StdErr.AtEndOfStream) stderr = e.StdErr.ReadAll();
  return { code: e.ExitCode, stdout: stdout, stderr: stderr };
}
function sha256(path) {
  var r = execCapture('certutil -hashfile ' + quoteCmdPath(path) + ' SHA256');
  if (r.code !== 0) throw new Error("certutil SHA256 failed for " + path + " :: " + r.stderr);
  var lines = r.stdout.split(/\r?\n/);
  var i, line;
  for (i = 0; i < lines.length; i++) {
    line = trim(lines[i]).replace(/\s+/g, "").toLowerCase();
    if (/^[0-9a-f]{64}$/.test(line)) return line;
  }
  throw new Error("SHA256 not found in certutil output for " + path);
}
function fileSize(path) { return fso.GetFile(path).Size; }
function listFiles(folderPath, arr) {
  var folder = fso.GetFolder(folderPath);
  var files = new Enumerator(folder.Files);
  for (; !files.atEnd(); files.moveNext()) { arr.push(String(files.item().Path)); }
  var subs = new Enumerator(folder.SubFolders);
  for (; !subs.atEnd(); subs.moveNext()) { listFiles(String(subs.item().Path), arr); }
}
function base64File(path) {
  var stream = new ActiveXObject("ADODB.Stream");
  stream.Type = 1;
  stream.Open();
  stream.LoadFromFile(path);
  var bytes = stream.Read();
  stream.Close();
  var dom = new ActiveXObject("MSXML2.DOMDocument");
  var node = dom.createElement("b64");
  node.dataType = "bin.base64";
  node.nodeTypedValue = bytes;
  return String(node.text).replace(/[\r\n]/g, "");
}
function jsonEscape(s) { return String(s).replace(/\\/g, "\\\\").replace(/"/g, "\\\"").replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t"); }
function jsonValue(v) {
  var t = typeof v;
  var i, parts, k;
  if (v === null) return "null";
  if (t === "string") return "\"" + jsonEscape(v) + "\"";
  if (t === "number") return String(v);
  if (t === "boolean") return v ? "true" : "false";
  if (v instanceof Array) {
    parts = [];
    for (i = 0; i < v.length; i++) parts.push(jsonValue(v[i]));
    return "[" + parts.join(",") + "]";
  }
  parts = [];
  for (k in v) { if (v.hasOwnProperty(k)) parts.push("\"" + jsonEscape(k) + "\":" + jsonValue(v[k])); }
  return "{" + parts.join(",") + "}";
}
function writeTextUtf8(path, text) {
  ensureFolderDeep(fso.GetParentFolderName(path));
  var st = new ActiveXObject("ADODB.Stream");
  st.Type = 2;
  st.Charset = "utf-8";
  st.Open();
  st.WriteText(text);
  st.SaveToFile(path, 2);
  st.Close();
}
function encodePath(path) {
  var parts = String(path).split("/");
  var i;
  for (i = 0; i < parts.length; i++) parts[i] = encodeURIComponent(parts[i]);
  return parts.join("/");
}
function http(method, url, token, body) {
  var xhr = new ActiveXObject("MSXML2.ServerXMLHTTP.6.0");
  xhr.open(method, url, false);
  xhr.setRequestHeader("User-Agent", "QIKVRT-Generic-Payload-Uploader");
  xhr.setRequestHeader("Accept", "application/vnd.github+json");
  xhr.setRequestHeader("X-GitHub-Api-Version", "2022-11-28");
  if (token) xhr.setRequestHeader("Authorization", "Bearer " + token);
  if (body !== null && body !== undefined) xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.send(body || null);
  return { status: xhr.status, text: String(xhr.responseText) };
}
function existingSha(owner, repo, branch, path, token) {
  var url = "https://api.github.com/repos/" + encodeURIComponent(owner) + "/" + encodeURIComponent(repo) + "/contents/" + encodePath(path) + "?ref=" + encodeURIComponent(branch);
  var r = http("GET", url, token, null);
  if (r.status === 404) return null;
  if (r.status < 200 || r.status >= 300) throw new Error("GET existing content failed " + r.status + " for " + path + " :: " + r.text);
  var m = /"sha"\s*:\s*"([^"]+)"/.exec(r.text);
  if (!m) throw new Error("existing sha not found for " + path);
  return m[1];
}
function uploadOne(owner, repo, branch, targetPath, localPath, token, message) {
  var b64 = base64File(localPath);
  var sha = existingSha(owner, repo, branch, targetPath, token);
  var body = { message: message, branch: branch, content: b64 };
  if (sha !== null) body.sha = sha;
  var url = "https://api.github.com/repos/" + encodeURIComponent(owner) + "/" + encodeURIComponent(repo) + "/contents/" + encodePath(targetPath);
  var r = http("PUT", url, token, jsonValue(body));
  if (r.status < 200 || r.status >= 300) throw new Error("PUT upload failed " + r.status + " for " + targetPath + " :: " + r.text);
  return sha === null ? "created" : "updated";
}
function splitRepo(s) {
  var v = trim(s);
  var p = v.split("/");
  if (p.length !== 2 || !p[0] || !p[1]) throw new Error("repository must look like Owner/name");
  return { owner: p[0], repo: p[1] };
}
function safeTargetRoot(s) {
  var v = trim(s).replace(/\\/g, "/");
  v = v.replace(/^\/+/, "").replace(/\/+$/, "");
  if (!v) throw new Error("target path empty");
  if (v.indexOf("..") >= 0) throw new Error("target path must not contain ..");
  return v;
}
function main() {
  out("QIKVRT_UPLOAD_START " + VERSION);
  var a = readLine("Accept copyright and license? Type JA or YES: ");
  if (!yes(a)) { out("QIKVRT_ACCEPTANCE BLOCK copyright/license not accepted"); return 10; }
  var po = readLine("Confirm Product Owner upload authorization? Type JA or YES: ");
  if (!yes(po)) { out("QIKVRT_ACCEPTANCE BLOCK product owner authorization not accepted"); return 11; }

  var payload = fso.BuildPath(root, "payload");
  if (!fso.FolderExists(payload)) { out("PAYLOAD_SCAN BLOCK payload folder missing"); return 20; }
  var files = [];
  listFiles(payload, files);
  var filtered = [];
  var i;
  for (i = 0; i < files.length; i++) {
    if (relPath(files[i], payload) !== "PUT_FILES_OR_FOLDERS_HERE.txt") filtered.push(files[i]);
  }
  if (filtered.length === 0) { out("PAYLOAD_SCAN BLOCK no payload files found; put files into payload folder"); return 21; }

  var defRepo = "Goldkelch/qik-vrt";
  var repoIn = readLine("Target repository [" + defRepo + "]: ");
  if (trim(repoIn) === "") repoIn = defRepo;
  var rr = splitRepo(repoIn);
  var branch = readLine("Branch [main]: ");
  if (trim(branch) === "") branch = "main";
  branch = trim(branch);
  var defRoot = "incoming/qikvrt_payloads/" + timestampUTC();
  var targetRoot = readLine("Target path [" + defRoot + "]: ");
  if (trim(targetRoot) === "") targetRoot = defRoot;
  targetRoot = safeTargetRoot(targetRoot);
  var mode = up(readLine("Mode DRYRUN or UPLOAD [DRYRUN]: "));
  if (mode === "") mode = "DRYRUN";
  if (mode !== "DRYRUN" && mode !== "UPLOAD") { out("MODE BLOCK choose DRYRUN or UPLOAD"); return 30; }

  var generated = fso.BuildPath(root, "qikvrt_generated");
  ensureFolderDeep(fso.BuildPath(generated, "registry"));
  ensureFolderDeep(fso.BuildPath(generated, "evidence"));
  ensureFolderDeep(fso.BuildPath(root, "logs"));
  var items = [];
  for (i = 0; i < filtered.length; i++) {
    var rp = relPath(filtered[i], payload);
    items.push({ local_path: filtered[i], relative_path: rp, target_path: targetRoot + "/payload/" + rp, size_bytes: fileSize(filtered[i]), sha256: sha256(filtered[i]) });
  }
  var manifest = {
    qikvrt_manifest_version: "1.0",
    kit_version: VERSION,
    purpose: "generic_payload_upload",
    target_repository: rr.owner + "/" + rr.repo,
    target_branch: branch,
    target_root: targetRoot,
    created_utc: timestampUTC(),
    product_owner_authorization: "accepted_interactively",
    boundaries: {
      no_git: true,
      no_embedded_token: true,
      no_remote_mutation_without_consent: true,
      no_global_scanning: true,
      no_self_propagation: true
    },
    payload_items: items
  };
  var manifestJsonPath = fso.BuildPath(generated, "registry\\QIKVRT_PAYLOAD_MANIFEST.json");
  var manifestMdPath = fso.BuildPath(generated, "registry\\QIKVRT_PAYLOAD_MANIFEST.md");
  writeTextUtf8(manifestJsonPath, jsonValue(manifest) + "\n");
  var md = "<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->\n<!-- Copyright (c) 2026 Ingolf Lohmann. -->\n# QIK-VRT Payload Manifest\n\nTarget: " + rr.owner + "/" + rr.repo + "\n\nBranch: " + branch + "\n\nTarget root: " + targetRoot + "\n\nItems:\n";
  for (i = 0; i < items.length; i++) md += "- `" + items[i].relative_path + "` sha256 `" + items[i].sha256 + "`\n";
  writeTextUtf8(manifestMdPath, md);
  var evidence = {
    qikvrt_evidence_version: "1.0",
    kit_version: VERSION,
    mode: mode,
    target_repository: rr.owner + "/" + rr.repo,
    target_branch: branch,
    target_root: targetRoot,
    payload_count: items.length,
    created_utc: timestampUTC(),
    status: mode === "DRYRUN" ? "DRYRUN_READY" : "UPLOAD_REQUESTED"
  };
  var evidenceJsonPath = fso.BuildPath(generated, "evidence\\QIKVRT_UPLOAD_EVIDENCE.json");
  var evidenceMdPath = fso.BuildPath(generated, "evidence\\QIKVRT_UPLOAD_EVIDENCE.md");
  writeTextUtf8(evidenceJsonPath, jsonValue(evidence) + "\n");
  writeTextUtf8(evidenceMdPath, "<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->\n<!-- Copyright (c) 2026 Ingolf Lohmann. -->\n# QIK-VRT Upload Evidence\n\nMode: " + mode + "\n\nTarget: " + rr.owner + "/" + rr.repo + "\n\nPayload files: " + items.length + "\n");

  out("PAYLOAD_SCAN PASS files=" + items.length);
  out("TARGET PASS repo=" + rr.owner + "/" + rr.repo + " branch=" + branch + " path=" + targetRoot);
  out("MANIFEST PASS " + manifestJsonPath);
  if (mode === "DRYRUN") {
    writeTextUtf8(fso.BuildPath(root, "logs\\UPLOAD_RESULT.txt"), "QIKVRT_UPLOAD_DRYRUN_PASS\nfiles=" + items.length + "\ntarget=" + rr.owner + "/" + rr.repo + "/" + targetRoot + "\n");
    writeTextUtf8(fso.BuildPath(root, "logs\\UPLOAD_RESULT.json"), jsonValue({ status: "DRYRUN_PASS", files: items.length, target_repository: rr.owner + "/" + rr.repo, target_root: targetRoot }) + "\n");
    out("QIKVRT_UPLOAD_DRYRUN_PASS");
    return 0;
  }

  var final = readLine("Remote upload will modify GitHub. Type UPLOAD to continue: ");
  if (up(final) !== "UPLOAD") { out("REMOTE_UPLOAD BLOCK final confirmation not provided"); return 40; }
  var token = readLine("Paste GitHub fine-grained token with Contents read/write: ");
  if (trim(token) === "") { out("TOKEN BLOCK empty token"); return 41; }
  var uploadList = [];
  for (i = 0; i < items.length; i++) uploadList.push({ local_path: items[i].local_path, target_path: items[i].target_path });
  uploadList.push({ local_path: manifestJsonPath, target_path: targetRoot + "/registry/QIKVRT_PAYLOAD_MANIFEST.json" });
  uploadList.push({ local_path: manifestMdPath, target_path: targetRoot + "/registry/QIKVRT_PAYLOAD_MANIFEST.md" });
  uploadList.push({ local_path: evidenceJsonPath, target_path: targetRoot + "/evidence/QIKVRT_UPLOAD_EVIDENCE.json" });
  uploadList.push({ local_path: evidenceMdPath, target_path: targetRoot + "/evidence/QIKVRT_UPLOAD_EVIDENCE.md" });
  var results = [];
  var msg = "QIK-VRT generic payload upload " + timestampUTC();
  for (i = 0; i < uploadList.length; i++) {
    out("UPLOAD " + (i+1) + "/" + uploadList.length + " " + uploadList[i].target_path);
    var action = uploadOne(rr.owner, rr.repo, branch, uploadList[i].target_path, uploadList[i].local_path, trim(token), msg);
    results.push({ target_path: uploadList[i].target_path, action: action });
  }
  writeTextUtf8(fso.BuildPath(root, "logs\\UPLOAD_RESULT.json"), jsonValue({ status: "UPLOAD_PASS", target_repository: rr.owner + "/" + rr.repo, target_root: targetRoot, files_uploaded: results.length, results: results }) + "\n");
  writeTextUtf8(fso.BuildPath(root, "logs\\UPLOAD_RESULT.txt"), "QIKVRT_UPLOAD_PASS\ntarget=" + rr.owner + "/" + rr.repo + "/" + targetRoot + "\nfiles_uploaded=" + results.length + "\n");
  out("QIKVRT_UPLOAD_PASS files=" + results.length);
  return 0;
}
try {
  WScript.Quit(main());
} catch (e) {
  err("QIKVRT_UPLOAD_EXCEPTION " + e.message);
  WScript.Quit(99);
}
