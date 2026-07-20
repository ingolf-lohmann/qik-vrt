// QIKVRT V2.13.4AT Autonomous Seed/Node Mesh Maintenance Installer
// Windows Script Host JScript. No PowerShell. No .ps1. No Git in installer.
// Token input is masked via a local HTA password dialog. Tokens are not printed.

var fso = new ActiveXObject("Scripting.FileSystemObject");
var shell = new ActiveXObject("WScript.Shell");
var GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe";
var SEED_DEFAULT = "Goldkelch/qik-vrt";
var NODE_DEFAULT = "ingolf-lohmann/qik-vrt";
var BRANCH_DEFAULT = "main";

function out(s) { WScript.StdOut.WriteLine(s); }
function write(s) { WScript.StdOut.Write(s); }
function trim(s) { return String(s).replace(/^\s+|\s+$/g, ""); }
function upper(s) { return String(s).toUpperCase(); }
function ynAccept(s) { s = upper(trim(s)); return s === "JA" || s === "J" || s === "YES" || s === "Y"; }
function jsonEscape(s) { return String(s).replace(/\\/g,"\\\\").replace(/"/g,"\\\"").replace(/\r/g,"\\r").replace(/\n/g,"\\n").replace(/\t/g,"\\t"); }
function apiPathEncode(path) { var parts = String(path).split("/"); for (var i=0;i<parts.length;i++) parts[i] = encodeURIComponent(parts[i]); return parts.join("/"); }
function sleep(ms) { WScript.Sleep(ms); }

function promptLine(label, def) {
  if (def !== null && def !== undefined && def !== "") write(label + " [" + def + "]: ");
  else write(label + ": ");
  var s = WScript.StdIn.ReadLine();
  s = trim(s);
  if (s === "" && def !== null && def !== undefined) return def;
  return s;
}

function which(cmd) {
  try {
    var e = shell.Exec("cmd /c where " + cmd + " 2>nul");
    while (e.Status === 0) sleep(50);
    return e.ExitCode === 0;
  } catch (ex) { return false; }
}

function tempName(prefix, ext) {
  var t = shell.ExpandEnvironmentStrings("%TEMP%");
  var n = prefix + "_" + String(new Date().getTime()) + "_" + String(Math.floor(Math.random()*1000000)) + ext;
  return fso.BuildPath(t, n);
}

function htaEscapeForJsString(s) {
  return String(s).replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/\r/g," ").replace(/\n/g," ");
}

function readSecretHidden(label) {
  var envName = label.indexOf("SEED") >= 0 ? "QIKVRT_SEED_TOKEN" : "QIKVRT_NODE_TOKEN";
  try {
    var envVal = shell.ExpandEnvironmentStrings("%" + envName + "%");
    if (envVal !== "%" + envName + "%" && trim(envVal) !== "") {
      out("MASKED_TOKEN_SOURCE " + envName + " environment variable present");
      return trim(envVal);
    }
  } catch (ex0) {}

  if (!which("mshta.exe")) {
    out("BLOCK TOKEN_MASKING_UNAVAILABLE: mshta.exe not found or disabled. Token will not be requested visibly.");
    out("Set " + envName + " in a secure local environment and rerun, or enable mshta for the local password dialog.");
    WScript.Quit(31);
  }
  var outPath = tempName("qikvrt_token", ".txt");
  var htaPath = tempName("qikvrt_token_prompt", ".hta");
  var html = "<html><head><title>QIKVRT masked token input</title>" +
    "<HTA:APPLICATION ID='qikvrt' APPLICATIONNAME='QIKVRT' BORDER='thin' CAPTION='yes' SHOWINTASKBAR='yes' SINGLEINSTANCE='yes' SYSMENU='yes' SCROLL='no' WINDOWSTATE='normal'/>" +
    "<script language='javascript'>\n" +
    "function esc(s){return s;}\n" +
    "function done(){var fso=new ActiveXObject('Scripting.FileSystemObject');var f=fso.CreateTextFile('" + htaEscapeForJsString(outPath) + "',true);f.Write(document.getElementById('pw').value);f.Close();window.close();}\n" +
    "function cancel(){window.close();}\n" +
    "function init(){window.resizeTo(720,240);document.getElementById('pw').focus();}\n" +
    "document.onkeydown=function(){if(event.keyCode==13)done(); if(event.keyCode==27)cancel();};\n" +
    "</script></head><body onload='init()' style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;margin:20px;'>" +
    "<div><b>" + htaEscapeForJsString(label) + "</b></div>" +
    "<p>The token is masked and will not be printed to the console. It is used in memory for this upload only.</p>" +
    "<input id='pw' type='password' style='width:650px;font-size:16px;' autocomplete='off'/>" +
    "<p><button onclick='done()' style='font-size:14px;'>OK</button> <button onclick='cancel()' style='font-size:14px;'>Cancel</button></p>" +
    "</body></html>";
  var h = fso.CreateTextFile(htaPath, true);
  h.Write(html);
  h.Close();
  out("MASKED_TOKEN_PROMPT opened for " + label);
  shell.Run("mshta.exe \"" + htaPath + "\"", 1, true);
  try { if (fso.FileExists(htaPath)) fso.DeleteFile(htaPath, true); } catch (del0) {}
  if (!fso.FileExists(outPath)) {
    out("BLOCK TOKEN_INPUT_CANCELLED for " + label);
    WScript.Quit(32);
  }
  var tf = fso.OpenTextFile(outPath, 1);
  var tok = tf.ReadAll();
  tf.Close();
  try { fso.DeleteFile(outPath, true); } catch (del1) {}
  tok = trim(tok);
  if (tok === "") {
    out("BLOCK EMPTY_TOKEN for " + label);
    WScript.Quit(33);
  }
  out("MASKED_TOKEN_RECEIVED " + label);
  return tok;
}

function httpRequest(method, url, token, body) {
  var req = null;
  try { req = new ActiveXObject("MSXML2.ServerXMLHTTP.6.0"); } catch (e1) {
    try { req = new ActiveXObject("MSXML2.ServerXMLHTTP"); } catch (e2) {
      req = new ActiveXObject("MSXML2.XMLHTTP");
    }
  }
  req.open(method, url, false);
  req.setRequestHeader("User-Agent", "QIKVRT-4AT-Installer");
  req.setRequestHeader("Accept", "application/vnd.github+json");
  req.setRequestHeader("X-GitHub-Api-Version", "2022-11-28");
  if (token && token !== "") req.setRequestHeader("Authorization", "Bearer " + token);
  if (body !== null && body !== undefined) req.setRequestHeader("Content-Type", "application/json; charset=utf-8");
  try { req.send(body === null || body === undefined ? null : body); }
  catch (ex) { return {status:0, text:String(ex)}; }
  return {status:req.status, text:req.responseText};
}

function fileBase64(path) {
  var stream = new ActiveXObject("ADODB.Stream");
  stream.Type = 1;
  stream.Open();
  stream.LoadFromFile(path);
  var bytes = stream.Read();
  stream.Close();
  var dom = new ActiveXObject("MSXML2.DOMDocument.6.0");
  var elem = dom.createElement("b64");
  elem.dataType = "bin.base64";
  elem.nodeTypedValue = bytes;
  return String(elem.text).replace(/[\r\n]/g, "");
}

function listFilesRecursive(root) {
  var arr = [];
  function walk(folder) {
    var f = fso.GetFolder(folder);
    var files = new Enumerator(f.Files);
    for (; !files.atEnd(); files.moveNext()) arr.push(String(files.item().Path));
    var subs = new Enumerator(f.SubFolders);
    for (; !subs.atEnd(); subs.moveNext()) walk(String(subs.item().Path));
  }
  walk(root);
  return arr;
}

function relPath(root, path) {
  var r = String(root);
  var p = String(path);
  if (p.toLowerCase().indexOf(r.toLowerCase()) === 0) p = p.substring(r.length);
  while (p.charAt(0) === "\\" || p.charAt(0) === "/") p = p.substring(1);
  return p.replace(/\\/g,"/");
}

function getExistingSha(repo, branch, targetPath, token) {
  var url = "https://api.github.com/repos/" + repo + "/contents/" + apiPathEncode(targetPath) + "?ref=" + encodeURIComponent(branch);
  var res = httpRequest("GET", url, token, null);
  if (res.status === 404) return "";
  if (res.status !== 200) {
    out("BLOCK GET_EXISTING_FAILED repo=" + repo + " path=" + targetPath + " http=" + res.status);
    out(res.text.substring(0, 600));
    WScript.Quit(41);
  }
  var m = /"sha"\s*:\s*"([^"]+)"/.exec(res.text);
  return m ? m[1] : "";
}

function uploadFile(repo, branch, targetPath, sourcePath, token, message) {
  var b64 = fileBase64(sourcePath);
  var sha = getExistingSha(repo, branch, targetPath, token);
  var body = "{\"message\":\"" + jsonEscape(message) + "\",\"branch\":\"" + jsonEscape(branch) + "\",\"content\":\"" + b64 + "\"";
  if (sha !== "") body += ",\"sha\":\"" + jsonEscape(sha) + "\"";
  body += "}";
  var url = "https://api.github.com/repos/" + repo + "/contents/" + apiPathEncode(targetPath);
  var res = httpRequest("PUT", url, token, body);
  if (res.status !== 200 && res.status !== 201) {
    out("BLOCK UPLOAD_FAILED repo=" + repo + " path=" + targetPath + " http=" + res.status);
    out(res.text.substring(0, 800));
    WScript.Quit(42);
  }
  out("PASS upload " + repo + " " + targetPath);
}

function uploadRole(role, repo, branch, token) {
  var root = fso.BuildPath(fso.GetAbsolutePathName("."), "roles\\" + role);
  if (!fso.FolderExists(root)) { out("BLOCK missing role folder " + root); WScript.Quit(43); }
  var files = listFilesRecursive(root);
  out("QIKVRT_UPLOAD role=" + role + " repo=" + repo + " branch=" + branch + " files=" + files.length);
  for (var i=0;i<files.length;i++) {
    var rp = relPath(root, files[i]);
    uploadFile(repo, branch, rp, files[i], token, "QIKVRT V2.13.4AT install " + role + " " + rp);
  }
}

function dispatchWorkflow(repo, branch, workflowFile, token) {
  var url = "https://api.github.com/repos/" + repo + "/actions/workflows/" + encodeURIComponent(workflowFile) + "/dispatches";
  var body = "{\"ref\":\"" + jsonEscape(branch) + "\"}";
  var res = httpRequest("POST", url, token, body);
  if (res.status !== 204) {
    out("BLOCK WORKFLOW_DISPATCH_FAILED repo=" + repo + " workflow=" + workflowFile + " http=" + res.status);
    out(res.text.substring(0, 800));
    WScript.Quit(51);
  }
  out("WORKFLOW_DISPATCH PASS " + repo + " " + workflowFile);
}

function contentExists(repo, branch, path, token) {
  var url = "https://api.github.com/repos/" + repo + "/contents/" + apiPathEncode(path) + "?ref=" + encodeURIComponent(branch);
  var res = httpRequest("GET", url, token, null);
  return res.status === 200;
}

function waitContent(label, repo, branch, path, token, maxSec) {
  var waited = 0;
  while (waited <= maxSec) {
    if (contentExists(repo, branch, path, token)) {
      out("WAIT_CONTENT PASS " + label + " " + repo + " " + path + " waited_sec=" + waited);
      return;
    }
    if (waited >= maxSec) break;
    sleep(10000);
    waited += 10;
    out("WAIT_CONTENT pending " + label + " waited_sec=" + waited);
  }
  out("BLOCK WAIT_CONTENT_TIMEOUT " + label + " " + repo + " " + path);
  WScript.Quit(52);
}

out("QIKVRT V2.13.4AT Autonomous Seed/Node Mesh Maintenance Installer");
out("No visible token prompt. Tokens are entered in a masked local password dialog.");
out("Implements: seed index aggregator, seed liveness/status, node heartbeat, node ack.");
var acc = promptLine("Accept copyright and license? Type JA or YES", "");
if (!ynAccept(acc)) { out("BLOCK COPYRIGHT_AND_LICENSE_NOT_ACCEPTED"); WScript.Quit(11); }
var auth = promptLine("Confirm Product Owner upload authorization? Type JA or YES", "");
if (!ynAccept(auth)) { out("BLOCK PRODUCT_OWNER_UPLOAD_NOT_AUTHORIZED"); WScript.Quit(12); }
var seedRepo = promptLine("Seed repository", SEED_DEFAULT);
var nodeRepo = promptLine("Node repository", NODE_DEFAULT);
var seedBranch = promptLine("Seed branch", BRANCH_DEFAULT);
var nodeBranch = promptLine("Node branch", BRANCH_DEFAULT);
out("Seed target: " + seedRepo + " @ " + seedBranch);
out("Node target: " + nodeRepo + " @ " + nodeBranch);
out("Mode DRYRUN performs local planning only and requires no token/network.");
var mode = upper(promptLine("Mode: DRYRUN or UPLOAD", "DRYRUN"));
if (mode !== "DRYRUN" && mode !== "UPLOAD") { out("BLOCK invalid mode"); WScript.Quit(13); }

if (mode === "DRYRUN") {
  out("DRYRUN seed files=" + listFilesRecursive(fso.BuildPath(fso.GetAbsolutePathName("."), "roles\\seed")).length);
  out("DRYRUN node files=" + listFilesRecursive(fso.BuildPath(fso.GetAbsolutePathName("."), "roles\\node")).length);
  out("DRYRUN expected seed outputs: registry/NODEMESH_INDEX.json, registry/NODEMESH_STATUS.json, registry/nodes/" + GUID + ".json");
  out("DRYRUN expected node outputs: qikvrt/runtime/onboarding/NODE_HEALTH.json, qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json");
  out("QIKVRT_4AT_INSTALL_FINAL PASS mode=DRYRUN");
  WScript.Quit(0);
}

out("UPLOAD mode selected. Tokens are requested in masked local dialogs.");
out("SEED token scope needed for " + seedRepo + ": Contents read/write and Actions/Workflow dispatch if workflows are triggered.");
var seedToken = readSecretHidden("SEED TOKEN for repository " + seedRepo);
var same = upper(promptLine("Use the same token also for NODE repository " + nodeRepo + "? Type YES only if this token has write access to that repo", "NO"));
var nodeToken = "";
if (same === "YES" || same === "JA" || same === "Y" || same === "J") {
  nodeToken = seedToken;
  out("TOKEN_REUSE_FOR_NODE explicitly accepted");
} else {
  out("NODE token scope needed for " + nodeRepo + ": Contents read/write and Actions/Workflow dispatch if workflows are triggered.");
  nodeToken = readSecretHidden("NODE TOKEN for repository " + nodeRepo);
}
var final = upper(promptLine("FINAL REMOTE MUTATION CONFIRMATION for BOTH repos. Type UPLOAD", ""));
if (final !== "UPLOAD") { out("BLOCK FINAL_UPLOAD_CONFIRMATION_NOT_GIVEN"); WScript.Quit(14); }

uploadRole("seed", seedRepo, seedBranch, seedToken);
uploadRole("node", nodeRepo, nodeBranch, nodeToken);

var trig = upper(promptLine("Trigger workflows now? Type YES for sequenced autonomous maintenance, ENTER to skip", ""));
if (trig === "YES" || trig === "JA" || trig === "Y" || trig === "J") {
  dispatchWorkflow(nodeRepo, nodeBranch, "qikvrt_node_health_publish.yml", nodeToken);
  waitContent("NODE_HEALTH", nodeRepo, nodeBranch, "qikvrt/runtime/onboarding/NODE_HEALTH.json", nodeToken, 180);

  dispatchWorkflow(seedRepo, seedBranch, "qikvrt_seed_registry_acceptance.yml", seedToken);
  waitContent("SEED_NODE_ENTRY", seedRepo, seedBranch, "registry/nodes/" + GUID + ".json", seedToken, 180);
  waitContent("SEED_NODEMESH_INDEX", seedRepo, seedBranch, "registry/NODEMESH_INDEX.json", seedToken, 180);
  waitContent("SEED_ACCEPTANCE_EVIDENCE", seedRepo, seedBranch, "evidence/seed_acceptance/" + GUID + ".json", seedToken, 180);

  dispatchWorkflow(seedRepo, seedBranch, "qikvrt_seed_mesh_maintenance.yml", seedToken);
  waitContent("SEED_NODEMESH_STATUS", seedRepo, seedBranch, "registry/NODEMESH_STATUS.json", seedToken, 180);
  waitContent("SEED_MAINTENANCE_LATEST", seedRepo, seedBranch, "evidence/seed_mesh_maintenance/LATEST.json", seedToken, 180);

  dispatchWorkflow(nodeRepo, nodeBranch, "qikvrt_node_seed_status_watch.yml", nodeToken);
  waitContent("NODE_SEED_ACCEPTANCE_STATUS", nodeRepo, nodeBranch, "qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json", nodeToken, 180);
  waitContent("NODE_SEED_LINK_EVIDENCE", nodeRepo, nodeBranch, "evidence/node_seed_link_status.json", nodeToken, 180);

  out("QIKVRT_AUTONOMOUS_MESH_MAINTENANCE_SEQUENCE PASS");
  out("QIKVRT_4AT_INSTALL_FINAL PASS mode=UPLOAD workflow_sequence=PASS");
  WScript.Quit(0);
}
out("QIKVRT_4AT_INSTALL_FINAL PASS mode=UPLOAD workflow_sequence=SKIPPED");
WScript.Quit(0);
