// QIKVRT V2.13.4AV2A Open Multi-Node Release Freeze HTA Token Fix Installer
// Windows Script Host JScript. No PowerShell. No .ps1. No Git command path.
// Uses GitHub REST API: Contents API and Releases API.

var VERSION = "QIKVRT_V2_13_4AV2A_OPEN_MULTI_NODE_RELEASE_FREEZE_HTA_TOKEN_FIX";
var DEFAULT_SEED_REPO = "Goldkelch/qik-vrt";
var DEFAULT_NODE_REPO = "ingolf-lohmann/qik-vrt";
var DEFAULT_BRANCH = "main";
var DEFAULT_RUN_ID = "4AV1_20260708T174034Z_709544";
var DEFAULT_SEED_TAG = "v2.13.4av1-seed-open-multi-node";
var DEFAULT_NODE_TAG = "v2.13.4av1-node-open-multi-node";
var NODE_GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe";
var API = "https://api.github.com";
var RAW = "https://raw.githubusercontent.com";
var fso = new ActiveXObject("Scripting.FileSystemObject");
var shell = new ActiveXObject("WScript.Shell");

function out(s) { WScript.StdOut.WriteLine(String(s)); }
function err(s) { WScript.StdErr.WriteLine(String(s)); }
function trim(s) { return String(s).replace(/^\s+|\s+$/g, ""); }
function upper(s) { return String(s).toUpperCase(); }
function nowUtc() {
  var d = new Date();
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  return d.getUTCFullYear() + pad(d.getUTCMonth()+1) + pad(d.getUTCDate()) + "T" + pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + pad(d.getUTCSeconds()) + "Z";
}
function rand6() { return String(Math.floor(Math.random() * 900000) + 100000); }
function promptLine(label, defval) {
  if (defval !== null && defval !== undefined && String(defval) !== "") {
    WScript.StdOut.Write(label + " [" + defval + "]: ");
  } else {
    WScript.StdOut.Write(label + ": ");
  }
  var v = WScript.StdIn.ReadLine();
  v = trim(v);
  if (v === "" && defval !== null && defval !== undefined) return String(defval);
  return v;
}
function confirmToken(ans, expected) { return upper(trim(ans)) === expected; }
function jsonEscape(s) {
  s = String(s);
  return s.replace(/\\/g,"\\\\").replace(/\"/g,"\\\"").replace(/\r/g,"\\r").replace(/\n/g,"\\n").replace(/\t/g,"\\t");
}
function b64Utf8(s) {
  var stream = new ActiveXObject("ADODB.Stream");
  stream.Type = 2;
  stream.Charset = "utf-8";
  stream.Open();
  stream.WriteText(String(s));
  stream.Position = 0;
  stream.Type = 1;
  var bytes = stream.Read();
  stream.Close();
  var dom = new ActiveXObject("MSXML2.DOMDocument");
  var el = dom.createElement("b64");
  el.dataType = "bin.base64";
  el.nodeTypedValue = bytes;
  return String(el.text).replace(/\r|\n/g, "");
}
function encodePath(p) {
  var parts = String(p).split("/");
  for (var i=0; i<parts.length; i++) parts[i] = encodeURIComponent(parts[i]);
  return parts.join("/");
}
function http(method, url, token, body) {
  var xhr = new ActiveXObject("MSXML2.ServerXMLHTTP.6.0");
  xhr.open(method, url, false);
  xhr.setRequestHeader("User-Agent", "QIKVRT-4AV2A-Release-Freeze-HTA-Token-Fix-Installer");
  xhr.setRequestHeader("Accept", "application/vnd.github+json");
  xhr.setRequestHeader("X-GitHub-Api-Version", "2022-11-28");
  if (token && token !== "") xhr.setRequestHeader("Authorization", "Bearer " + token);
  if (body !== null && body !== undefined) xhr.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  xhr.send(body === null || body === undefined ? null : body);
  return { status: xhr.status, text: String(xhr.responseText), headers: String(xhr.getAllResponseHeaders()) };
}
function rawExists(repo, branch, path) {
  var url = RAW + "/" + repo + "/" + encodeURIComponent(branch) + "/" + encodePath(path) + "?qikvrt_cache_bust=" + encodeURIComponent(nowUtc()+rand6());
  var r = http("GET", url, "", null);
  return r.status >= 200 && r.status < 300;
}
function getExistingSha(repo, branch, path, token) {
  var url = API + "/repos/" + repo + "/contents/" + encodePath(path) + "?ref=" + encodeURIComponent(branch);
  var r = http("GET", url, token, null);
  if (r.status === 404) return "";
  if (r.status < 200 || r.status >= 300) {
    throw new Error("GET_CONTENT_FAILED status=" + r.status + " repo=" + repo + " path=" + path + " body=" + r.text);
  }
  var m = /"sha"\s*:\s*"([0-9a-fA-F]+)"/.exec(r.text);
  if (!m) throw new Error("GET_CONTENT_SHA_PARSE_FAILED repo=" + repo + " path=" + path);
  return m[1];
}
function putContent(repo, branch, path, text, message, token) {
  var sha = getExistingSha(repo, branch, path, token);
  var payload = "{" +
    "\"message\":\"" + jsonEscape(message) + "\"," +
    "\"branch\":\"" + jsonEscape(branch) + "\"," +
    "\"content\":\"" + b64Utf8(text) + "\"" +
    (sha !== "" ? ",\"sha\":\"" + sha + "\"" : "") +
    "}";
  var url = API + "/repos/" + repo + "/contents/" + encodePath(path);
  var r = http("PUT", url, token, payload);
  if (r.status < 200 || r.status >= 300) {
    throw new Error("PUT_CONTENT_FAILED status=" + r.status + " repo=" + repo + " path=" + path + " body=" + r.text);
  }
  out("PASS upload " + repo + " " + path);
}
function getReleaseByTag(repo, tag, token) {
  var r = http("GET", API + "/repos/" + repo + "/releases/tags/" + encodeURIComponent(tag), token, null);
  return r;
}
function getTagRef(repo, tag, token) {
  return http("GET", API + "/repos/" + repo + "/git/ref/tags/" + encodeURIComponent(tag), token, null);
}
function createReleaseIfMissing(repo, branch, tag, name, body, token) {
  var rel = getReleaseByTag(repo, tag, token);
  if (rel.status >= 200 && rel.status < 300) {
    out("PASS release_exists_no_mutation " + repo + " " + tag);
    return;
  }
  if (rel.status !== 404) {
    throw new Error("RELEASE_LOOKUP_FAILED status=" + rel.status + " repo=" + repo + " tag=" + tag + " body=" + rel.text);
  }
  var tagRef = getTagRef(repo, tag, token);
  if (tagRef.status >= 200 && tagRef.status < 300) {
    out("PASS existing_tag_detected_no_move " + repo + " " + tag);
  } else if (tagRef.status === 404) {
    out("INFO tag_missing_release_api_will_create_tag " + repo + " " + tag + " target=" + branch);
  } else {
    throw new Error("TAG_REF_LOOKUP_FAILED status=" + tagRef.status + " repo=" + repo + " tag=" + tag + " body=" + tagRef.text);
  }
  var payload = "{" +
    "\"tag_name\":\"" + jsonEscape(tag) + "\"," +
    "\"target_commitish\":\"" + jsonEscape(branch) + "\"," +
    "\"name\":\"" + jsonEscape(name) + "\"," +
    "\"body\":\"" + jsonEscape(body) + "\"," +
    "\"draft\":false," +
    "\"prerelease\":false," +
    "\"make_latest\":\"false\"" +
    "}";
  var r = http("POST", API + "/repos/" + repo + "/releases", token, payload);
  if (r.status < 200 || r.status >= 300) {
    throw new Error("CREATE_RELEASE_FAILED status=" + r.status + " repo=" + repo + " tag=" + tag + " body=" + r.text);
  }
  out("PASS release_created " + repo + " " + tag);
}
function jsStringLiteral(s) {
  var r = String(s);
  r = r.replace(/\\/g,"\\\\");
  r = r.replace(/'/g,"\\'");
  r = r.replace(/\r/g,"\\r");
  r = r.replace(/\n/g,"\\n");
  return r;
}
function htmlEscape(s) {
  var r = String(s);
  r = r.replace(/&/g,"&amp;");
  r = r.replace(/</g,"&lt;");
  r = r.replace(/>/g,"&gt;");
  r = r.replace(/"/g,"&quot;");
  return r;
}
function maskedTokenPrompt(title) {
  var tmpDir = shell.ExpandEnvironmentStrings("%TEMP%");
  var stamp = nowUtc() + "_" + rand6();
  var hta = fso.BuildPath(tmpDir, "qikvrt_token_prompt_" + stamp + ".hta");
  var outFile = fso.BuildPath(tmpDir, "qikvrt_token_value_" + stamp + ".txt");
  var html = "<!DOCTYPE html>\r\n" +
    "<html>\r\n<head>\r\n<title>QIKVRT Token Prompt</title>\r\n" +
    "<HTA:APPLICATION ID=\"qikvrt\" APPLICATIONNAME=\"QIKVRT\" BORDER=\"thin\" CAPTION=\"yes\" SHOWINTASKBAR=\"yes\" SINGLEINSTANCE=\"yes\" WINDOWSTATE=\"normal\">\r\n" +
    "<script language=\"javascript\" type=\"text/javascript\">\r\n" +
    "var qikvrtOutFile='" + jsStringLiteral(outFile) + "';\r\n" +
    "function qikvrtWriteToken(){\r\n" +
    "  var v=document.getElementById('qikvrt_token').value;\r\n" +
    "  var fso=new ActiveXObject('Scripting.FileSystemObject');\r\n" +
    "  var f=fso.CreateTextFile(qikvrtOutFile,true);\r\n" +
    "  f.Write(v); f.Close(); window.close();\r\n" +
    "}\r\n" +
    "function qikvrtCancel(){ window.close(); }\r\n" +
    "function window.onload(){ window.resizeTo(680,210); document.getElementById('qikvrt_token').focus(); }\r\n" +
    "function document.onkeydown(){ if (event.keyCode==13) qikvrtWriteToken(); if (event.keyCode==27) qikvrtCancel(); }\r\n" +
    "</script>\r\n</head>\r\n" +
    "<body style=\"font-family:Segoe UI,Arial,sans-serif;font-size:12pt\">\r\n" +
    "<p>" + htmlEscape(title) + "</p>\r\n" +
    "<input id=\"qikvrt_token\" type=\"password\" style=\"width:620px\" autocomplete=\"off\"/>\r\n" +
    "<p><input type=\"button\" value=\"OK\" onclick=\"qikvrtWriteToken()\"/> <input type=\"button\" value=\"Cancel\" onclick=\"qikvrtCancel()\"/></p>\r\n" +
    "</body>\r\n</html>\r\n";
  var f = fso.CreateTextFile(hta, true);
  f.Write(html);
  f.Close();
  out("MASKED_TOKEN_PROMPT opened for " + title);
  shell.Run("mshta.exe \"" + hta + "\"", 1, true);
  var token = "";
  if (fso.FileExists(outFile)) {
    var tf = fso.OpenTextFile(outFile, 1, false);
    token = tf.ReadAll();
    tf.Close();
  }
  try { if (fso.FileExists(hta)) fso.DeleteFile(hta, true); } catch(e1) {}
  try { if (fso.FileExists(outFile)) fso.DeleteFile(outFile, true); } catch(e2) {}
  token = trim(token);
  if (token === "") throw new Error("MASKED_TOKEN_EMPTY_OR_CANCELLED " + title);
  out("MASKED_TOKEN_RECEIVED " + title);
  return token;
}
function evidenceJson(role, repo, branch, tag, runId, createdUtc) {
  var lines = [];
  lines.push("{");
  lines.push("  \"qikvrt_event\": \"4AV2A_OPEN_MULTI_NODE_RELEASE_FREEZE_HTA_TOKEN_FIX\",");
  lines.push("  \"version\": \"" + VERSION + "\",");
  lines.push("  \"role\": \"" + role + "\",");
  lines.push("  \"repository\": \"" + repo + "\",");
  lines.push("  \"branch\": \"" + branch + "\",");
  lines.push("  \"tag\": \"" + tag + "\",");
  lines.push("  \"reference_run_id\": \"" + runId + "\",");
  lines.push("  \"reference_state\": \"4AV1_OPEN_MULTI_NODE_REVALIDATION_PASS\",");
  lines.push("  \"guid\": \"" + NODE_GUID + "\",");
  lines.push("  \"fixed_node_count\": false,");
  lines.push("  \"open_node_registry\": true,");
  lines.push("  \"future_nodes_without_installer_change\": true,");
  lines.push("  \"no_tag_move\": true,");
  lines.push("  \"no_release_overwrite\": true,");
  lines.push("  \"created_utc\": \"" + createdUtc + "\",");
  lines.push("  \"status\": \"PASS_REQUESTED_BY_OWNER_INSTALLER\",");
  lines.push("  \"boundaries\": {");
  lines.push("    \"no_global_scanning\": true,");
  lines.push("    \"no_self_propagation\": true,");
  lines.push("    \"no_remote_mutation_without_authorization\": true,");
  lines.push("    \"installer_uses_github_api_not_git\": true,");
  lines.push("    \"no_embedded_token\": true");
  lines.push("  }");
  lines.push("}");
  return lines.join("\n") + "\n";
}
function evidenceMd(role, repo, branch, tag, runId, createdUtc) {
  return "# QIK-VRT 4AV2A Open Multi-Node Release Freeze HTA Token Fix\n\n" +
    "Role: " + role + "\n\n" +
    "Repository: `" + repo + "`\n\n" +
    "Branch: `" + branch + "`\n\n" +
    "Tag: `" + tag + "`\n\n" +
    "Reference run: `" + runId + "`\n\n" +
    "Reference state: `4AV1_OPEN_MULTI_NODE_REVALIDATION_PASS`\n\n" +
    "Fixed node count: `false`\n\n" +
    "Open node registry: `true`\n\n" +
    "Future nodes without installer change: `true`\n\n" +
    "No tag move: `true`\n\n" +
    "No release overwrite: `true`\n\n" +
    "Created UTC: `" + createdUtc + "`\n\n" +
    "## Boundaries\n\n" +
    "- No global scanning.\n" +
    "- No self propagation.\n" +
    "- No remote mutation without Product Owner authorization.\n" +
    "- Installer uses GitHub API; no Git command path.\n" +
    "- No embedded token.\n\n" +
    "Status: `PASS_REQUESTED_BY_OWNER_INSTALLER`\n";
}
function releaseBody(role, repo, tag, runId) {
  return "QIK-VRT 4AV2 Open Multi-Node Release Freeze\n\n" +
    "Role: " + role + "\n\n" +
    "Repository: " + repo + "\n\n" +
    "Tag: " + tag + "\n\n" +
    "Reference run: " + runId + "\n\n" +
    "Reference state: 4AV1_OPEN_MULTI_NODE_REVALIDATION_PASS\n\n" +
    "This release freezes the open multi-node architecture state: fixed_node_count=false, open_node_registry=true, future_nodes_without_installer_change=true.\n\n" +
    "Safety boundaries: no global scanning, no self propagation, no foreign repository write by workflows, no remote mutation without authorization.\n\n" +
    "Known boundary: full byte-exact repository rehash is not asserted by this installer.\n";
}
function main() {
  out("QIKVRT V2.13.4AV2A Open Multi-Node Release Freeze HTA Token Fix Installer");
  out("No visible token prompt. Freezes the 4AV1 open multi-node PASS run as public Seed/Node releases.");
  var a1 = promptLine("Accept copyright and license? Type JA or YES", "");
  if (!(confirmToken(a1,"JA") || confirmToken(a1,"YES"))) throw new Error("COPYRIGHT_LICENSE_ACCEPTANCE_BLOCK");
  var a2 = promptLine("Confirm Product Owner release authorization? Type JA or YES", "");
  if (!(confirmToken(a2,"JA") || confirmToken(a2,"YES"))) throw new Error("PRODUCT_OWNER_AUTHORIZATION_BLOCK");
  var seedRepo = promptLine("Seed repository", DEFAULT_SEED_REPO);
  var nodeRepo = promptLine("Node repository", DEFAULT_NODE_REPO);
  var seedBranch = promptLine("Seed branch", DEFAULT_BRANCH);
  var nodeBranch = promptLine("Node branch", DEFAULT_BRANCH);
  var runId = promptLine("Reference 4AV1 PASS run id", DEFAULT_RUN_ID);
  var seedTag = promptLine("Seed release tag", DEFAULT_SEED_TAG);
  var nodeTag = promptLine("Node release tag", DEFAULT_NODE_TAG);
  out("Seed target: " + seedRepo + " @ " + seedBranch + " tag=" + seedTag);
  out("Node target: " + nodeRepo + " @ " + nodeBranch + " tag=" + nodeTag);
  out("Reference run id: " + runId);
  var mode = upper(promptLine("Mode: DRYRUN or RELEASE", "DRYRUN"));
  if (mode !== "DRYRUN" && mode !== "RELEASE") throw new Error("INVALID_MODE " + mode);
  if (mode === "DRYRUN") {
    out("DRYRUN seed evidence paths=3 release_tag=" + seedTag);
    out("DRYRUN node evidence paths=3 release_tag=" + nodeTag);
    out("DRYRUN no token/network/release mutation");
    out("QIKVRT_4AV2A_RELEASE_FREEZE_FINAL PASS mode=DRYRUN");
    return 0;
  }
  out("RELEASE mode selected. Tokens are requested in masked local dialogs.");
  out("SEED token scope needed for " + seedRepo + ": Contents read/write and Releases/API write.");
  var seedToken = maskedTokenPrompt("SEED TOKEN for repository " + seedRepo);
  var reuse = upper(promptLine("Use the same token also for NODE repository " + nodeRepo + "? Type YES only if this token has write access to that repo", "NO"));
  var nodeToken = seedToken;
  if (reuse !== "YES") {
    out("NODE token scope needed for " + nodeRepo + ": Contents read/write and Releases/API write.");
    nodeToken = maskedTokenPrompt("NODE TOKEN for repository " + nodeRepo);
  } else {
    out("TOKEN_REUSE_CONFIRMED for NODE repository " + nodeRepo);
  }
  var final = promptLine("FINAL RELEASE FREEZE CONFIRMATION for BOTH repos. Type RELEASE", "");
  if (upper(final) !== "RELEASE") throw new Error("FINAL_RELEASE_CONFIRMATION_BLOCK");
  var created = nowUtc();
  out("QIKVRT_RELEASE_FREEZE role=seed repo=" + seedRepo + " tag=" + seedTag);
  var seedJson = evidenceJson("seed", seedRepo, seedBranch, seedTag, runId, created);
  var seedMd = evidenceMd("seed", seedRepo, seedBranch, seedTag, runId, created);
  putContent(seedRepo, seedBranch, "release/freezes/4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.json", seedJson, "QIKVRT 4AV2 seed release freeze evidence", seedToken);
  putContent(seedRepo, seedBranch, "release/freezes/4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md", seedMd, "QIKVRT 4AV2 seed release freeze evidence", seedToken);
  putContent(seedRepo, seedBranch, "docs/QIKVRT_4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md", seedMd, "QIKVRT 4AV2 seed release freeze doc", seedToken);
  createReleaseIfMissing(seedRepo, seedBranch, seedTag, "QIK-VRT v2.13.4AV1 Seed Open Multi-Node Release Freeze", releaseBody("seed", seedRepo, seedTag, runId), seedToken);
  out("QIKVRT_RELEASE_FREEZE role=node repo=" + nodeRepo + " tag=" + nodeTag);
  var nodeJson = evidenceJson("node", nodeRepo, nodeBranch, nodeTag, runId, created);
  var nodeMd = evidenceMd("node", nodeRepo, nodeBranch, nodeTag, runId, created);
  putContent(nodeRepo, nodeBranch, "release/freezes/4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.json", nodeJson, "QIKVRT 4AV2 node release freeze evidence", nodeToken);
  putContent(nodeRepo, nodeBranch, "release/freezes/4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md", nodeMd, "QIKVRT 4AV2 node release freeze evidence", nodeToken);
  putContent(nodeRepo, nodeBranch, "docs/QIKVRT_4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md", nodeMd, "QIKVRT 4AV2 node release freeze doc", nodeToken);
  createReleaseIfMissing(nodeRepo, nodeBranch, nodeTag, "QIK-VRT v2.13.4AV1 Node Open Multi-Node Release Freeze", releaseBody("node", nodeRepo, nodeTag, runId), nodeToken);
  out("QIKVRT_4AV2A_RELEASE_FREEZE_FINAL PASS mode=RELEASE reference_run=" + runId);
  return 0;
}
try {
  var ec = main();
  WScript.Quit(ec);
} catch (e) {
  err("BLOCK " + e.message);
  WScript.Quit(1);
}
