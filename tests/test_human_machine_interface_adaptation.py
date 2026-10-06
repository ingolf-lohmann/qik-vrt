import json
import hashlib
import html
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
MATRIX = ROOT / "state/interface_adaptation/EVALUATION_MATRIX.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
ENTRYPOINT = ROOT / "AI"
BOOTLOADER = ROOT / "tools/ai_runtime_bootloader.py"
MONITOR = ROOT / "docs/monitor/index.html"
FEEDBACK_EVIDENCE = ROOT / "evidence/monitor-feedback"

# Execute the actual inline emitters, not a reimplementation of their wording.
# DOM storage is minimal: browser interaction/accessibility needs its own witness.
MONITOR_REPLAY = r"""
const fs = require('node:fs'), vm = require('node:vm');
(async () => {
  const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
  const elements = Object.fromEntries(['token','mode','clock','repos','log'].map(id => [id,{value:'',textContent:'',innerHTML:''}]));
  let faults = spec.faults || [], time = Date.parse(spec.time), calls = [];
  const api = 'https://api.github.com', authority = api + '/repos/Goldkelch/qik-vrt';
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [time])); } static now() { return time; } }
  function match(f, url) {
    return url.startsWith(authority) && (f.path === '*' || (f.path ? url.includes('/'+f.path) : url === authority));
  }
  const context = vm.createContext({
    Date:Clock, setInterval:()=>1, clearInterval:()=>{},
    sessionStorage:{getItem:()=>spec.token || '',setItem:()=>{},removeItem:()=>{}},
    document:{getElementById:id=>elements[id]},
    fetch:async (url, options) => {
      calls.push({url,method:options.method || 'GET',authorization_present:!!options.headers.Authorization});
      const fault = faults.find(f => match(f,url));
      if (fault?.network) { const error = new Error(fault.message || 'Failed to fetch'); error.name = fault.name || 'TypeError'; throw error; }
      const status = fault?.status || 200;
      const headers = fault?.headers || {};
      let value = url.includes('/actions/runs') ? {workflow_runs:[{id:7,name:'CI',status:'completed',conclusion:'action_required',head_sha:'a'.repeat(40),html_url:'https://github.com/example/run/7'}]} :
        url.includes('/pulls?') ? [{number:1,head:{sha:'a'.repeat(40)},updated_at:spec.time,draft:true,html_url:'https://github.com/example/pull/1'}] :
        url.includes('/commits?') ? [{sha:'a'.repeat(40)}] : {default_branch:'main'};
      if (fault?.malformed) value = {};
      return {ok:status < 400,status,statusText:fault?.status_text || 'OK',headers:{get:key=>headers[key] ?? null},
        json:async()=>{if(fault?.json_error)throw new SyntaxError('Unexpected token in JSON');return value;}};
    }
  });
  const source = spec.source.match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(source, context, {timeout:1000});
  if(spec.double_refresh)context.refreshAll();
  const drain = async()=>{for(let i=0;i<12;i++)await new Promise(resolve=>setImmediate(resolve));};
  const snapshot=()=>({clock:elements.clock.textContent,body:elements.repos.innerHTML,log:elements.log.textContent,calls:calls.slice()});
  await drain(); const snapshots=[snapshot()];
  for(const transition of spec.transitions || []) {
    faults=transition.faults;time+=1000;
    await context.refreshAll();await drain();snapshots.push(snapshot());
  }
  process.stdout.write(JSON.stringify({snapshots}));
})().catch(error=>{process.stderr.write(String(error.stack));process.exitCode=1;});
"""


def replay_monitor(faults, *, baseline=False, transitions=None, token="", double_refresh=False):
    observation = json.loads((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_text())
    path = FEEDBACK_EVIDENCE / "baseline-index.html" if baseline else MONITOR
    payload = {"source": path.read_text(), "time": observation["observed_at"], "faults": faults,
               "transitions": transitions or [], "token": token, "double_refresh": double_refresh}
    result = subprocess.run(["node", "-e", MONITOR_REPLAY], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=15, check=True)
    return json.loads(result.stdout)["snapshots"]


def captured_404():
    observation = json.loads((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_text())
    return {key: observation[key] for key in ("status", "status_text", "headers")}


def diagnostics(snapshot):
    return [json.loads(html.unescape(value)) for value in re.findall(r'<pre[^>]*>(.*?)</pre>', snapshot["body"], re.S)]


def feedback_report():
    fault = captured_404()
    before = replay_monitor([fault], baseline=True)[0]
    after = replay_monitor([fault])[0]
    labels = ["Zustand", "Auswirkung", "Ursache / Unsicherheit", "Nächster Schritt", "Reparaturfortschritt"]
    fields = dict(re.findall(r'<dt>(.*?)</dt><dd>(.*?)</dd>', after["body"], re.S))
    observation = json.loads((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_text())
    original = f'{fault["status"]} {fault["status_text"]}; remaining={fault["headers"]["x-ratelimit-remaining"]}'
    return {
        "schema": "qikvrt_monitor_feedback_comparison_v1",
        "case_id": "AUTHORITY_REPOSITORY_HTTP_404", "language": "de-DE",
        "method": "Controlled replay of the captured HTTP status/text/headers through both actual HTML emitters in Node vm; synthetic sibling responses held identical.",
        "baseline_commit": "cf5e10162c946df70d5d8547d58ad311ac29a0b3",
        "baseline_tree": "1ae1a72040364dc2c0aa62925b6774685f508b9d",
        "baseline_source_blob": "0e3f2303c0bab85ca40faf9922514e031e7bd2b6",
        "baseline_source_sha256": hashlib.sha256((FEEDBACK_EVIDENCE / "baseline-index.html").read_bytes()).hexdigest(),
        "candidate_source_sha256": hashlib.sha256(MONITOR.read_bytes()).hexdigest(),
        "observation_sha256": hashlib.sha256((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_bytes()).hexdigest(),
        "before": {"visible_feedback": before["clock"], "event_log": before["log"],
                   "explicit_required_explanation_fields": 0},
        "after": {"visible_feedback": after["clock"],
                  "explanations": {label: html.unescape(fields[label]) for label in labels},
                  "diagnostics": diagnostics(after),
                  "explicit_required_explanation_fields": sum(label in fields for label in labels)},
        "automated_measurements": {
            "explicit_required_explanation_fields_before": 0, "explicit_required_explanation_fields_after": 5,
            "original_error_retained": original == diagnostics(after)[0]["original_error"],
            "status_retained": observation["status"] == diagnostics(after)[0]["status"],
            "provider_request_id_retained": observation["headers"]["x-github-request-id"] == diagnostics(after)[0]["provider_request_id"],
            "source_url_retained": observation["url"] == diagnostics(after)[0]["source_url"],
            "requests_before": len(before["calls"]), "requests_after": len(after["calls"]),
            "successful_sibling_visible_before": "ingolf-lohmann/qik-vrt" in before["body"],
            "successful_sibling_visible_after": "ingolf-lohmann/qik-vrt" in after["body"]},
        "human_comprehension": {"state": "NOT_MEASURED", "participants": 0,
            "understanding_rate_before": None, "understanding_rate_after": None,
            "clarification_requests": None, "time_to_identify_next_action_ms": None,
            "comprehension_improvement_measured": False},
        "boundaries": {"controlled_replay_is_live_deployment": False,
            "automated_field_presence_is_human_comprehension": False,
            "provider_404_cause_established": False, "runtime_fault_repaired": False,
            "predecessor_evidence_transfer": False, "EFFECT_ACK_DONE": False}
    }


class TestMonitorFeedback(unittest.TestCase):
    def test_persisted_comparison_matches_the_current_emitters(self):
        recorded = json.loads((FEEDBACK_EVIDENCE / "authority-404-before-after.json").read_text())
        self.assertEqual(recorded, feedback_report())

    def test_captured_observation_and_baseline_have_exact_bindings(self):
        observation = json.loads((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_text())
        self.assertEqual(observation["status"], 404)
        self.assertEqual(hashlib.sha256(observation["response_body"].encode()).hexdigest(), observation["response_sha256"])
        raw = (FEEDBACK_EVIDENCE / "baseline-index.html").read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual(blob, "0e3f2303c0bab85ca40faf9922514e031e7bd2b6")

    def test_real_404_before_after_and_original_diagnostics(self):
        report = feedback_report()
        self.assertEqual(report["after"]["explicit_required_explanation_fields"], 5)
        metrics = report["automated_measurements"]
        for key in ("original_error_retained", "status_retained", "provider_request_id_retained", "source_url_retained"):
            self.assertTrue(metrics[key], key)
        self.assertEqual(metrics["requests_before"], metrics["requests_after"])
        self.assertFalse(metrics["successful_sibling_visible_before"])
        self.assertTrue(metrics["successful_sibling_visible_after"])
        self.assertIn("nicht geklärt", report["after"]["explanations"]["Ursache / Unsicherheit"])
        self.assertFalse(report["human_comprehension"]["comprehension_improvement_measured"])

    def test_distinct_http_failures_do_not_invent_the_same_cause(self):
        cases = [(403,"0","Der Anbieter begrenzt"), (403,"23","Der Zugriff"),
                 (401,"23","Der Zugriff"), (429,None,"Der Anbieter begrenzt"),
                 (502,"23","Serverfehler")]
        for status, remaining, expected in cases:
            with self.subTest(status=status, remaining=remaining):
                fault = {"status":status,"status_text":"TEST", "headers":{"x-ratelimit-remaining":remaining,"retry-after":"30"}}
                snapshot = replay_monitor([fault])[0]
                self.assertIn(expected, snapshot["body"])
                self.assertIn("nicht geklärt", snapshot["body"])
                self.assertEqual(diagnostics(snapshot)[0]["status"], status)
                if status in (429,) or remaining == "0":
                    self.assertIn("erst danach", snapshot["body"])
                    self.assertEqual(diagnostics(snapshot)[0]["retry_after"], "30")

    def test_network_error_does_not_claim_a_server_failure(self):
        snapshot = replay_monitor([{"network":True}])[0]
        self.assertIn("keine HTTP-Antwort", snapshot["body"])
        self.assertIsNone(diagnostics(snapshot)[0]["status"])
        self.assertEqual(diagnostics(snapshot)[0]["error_name"], "TypeError")
        self.assertNotIn("meldet einen Serverfehler", snapshot["body"])

    def test_json_and_shape_failures_are_not_mislabelled_as_network_errors(self):
        for fault, phase in [({"json_error":True}, "JSON"), ({"path":"actions", "malformed":True}, "EVALUATION")]:
            with self.subTest(phase=phase):
                snapshot = replay_monitor([fault])[0]
                self.assertIn("ausgewertet", snapshot["body"])
                self.assertEqual(diagnostics(snapshot)[0]["phase"], phase)
                self.assertNotIn("lieferte keine HTTP-Antwort", snapshot["body"])

    def test_multiple_failures_and_successful_sibling_are_all_visible(self):
        fault = {**captured_404(), "path":"*"}
        snapshot = replay_monitor([fault])[0]
        self.assertEqual(len(diagnostics(snapshot)), 4)
        self.assertEqual(len({row["source_url"] for row in diagnostics(snapshot)}), 4)
        self.assertIn("ingolf-lohmann/qik-vrt", snapshot["body"])
        self.assertIn("1 von 2", snapshot["clock"])

    def test_previous_good_data_stays_old_then_failure_clears_on_recovery(self):
        initial, failed, recovered = replay_monitor([], transitions=[{"faults":[captured_404()]},{"faults":[]}])
        observation = json.loads((FEEDBACK_EVIDENCE / "authority-404-observation.json").read_text())
        initial_time = observation["observed_at"].replace("+00:00", "Z")
        # JS renders milliseconds, retaining the original successful observation.
        initial_time = initial_time[:23] + "Z"
        self.assertIn(initial_time, initial["body"])
        self.assertIn(initial_time, failed["body"])
        self.assertIn("Letzter erfolgreicher Stand", failed["body"])
        self.assertIn("veraltet", failed["body"])
        self.assertNotIn("Readback offen", recovered["body"])
        self.assertIn("keine Runtime-Reparatur damit belegt", recovered["log"])

    def test_unchanged_failure_is_not_logged_again_but_details_are_fresh(self):
        first_fault = captured_404()
        changed_headers = {**first_fault["headers"],"x-github-request-id":"NEW-REQUEST","x-ratelimit-remaining":"55"}
        first, second = replay_monitor([first_fault], transitions=[{"faults":[{**first_fault,"headers":changed_headers}]}])
        self.assertEqual(first["log"], second["log"])
        self.assertNotEqual(diagnostics(first)[0]["observed_at"], diagnostics(second)[0]["observed_at"])
        self.assertEqual(diagnostics(second)[0]["provider_request_id"], "NEW-REQUEST")

    def test_overlapping_refresh_does_not_duplicate_requests(self):
        snapshot = replay_monitor([captured_404()], double_refresh=True)[0]
        self.assertEqual(len(snapshot["calls"]), 8)
        self.assertTrue(all(call["method"] == "GET" for call in snapshot["calls"]))

    def test_diagnostics_escape_markup_and_redact_secrets(self):
        message = '<img src=x onerror=alert(1)> Bearer TOPSECRET ghp_FAKESECRET https://example.test/?token=QUERYSECRET HTTP 404'
        snapshot = replay_monitor([{"network":True,"message":message}])[0]
        combined = snapshot["body"] + snapshot["log"]
        for secret in ("TOPSECRET", "ghp_FAKESECRET", "QUERYSECRET"):
            self.assertNotIn(secret, combined)
        self.assertNotIn("<img", snapshot["body"])
        self.assertIn("HTTP 404", diagnostics(snapshot)[0]["original_error"])
        self.assertIn("[REDACTED]", combined)

    def test_authorization_is_not_copied_into_feedback(self):
        snapshot = replay_monitor([captured_404()], token="TEST_SESSION_SECRET")[0]
        self.assertTrue(all(call["authorization_present"] for call in snapshot["calls"]))
        self.assertNotIn("TEST_SESSION_SECRET", snapshot["body"] + snapshot["log"])

    def test_workflow_machine_state_is_preserved_without_approval_claim(self):
        snapshot = replay_monitor([])[0]
        self.assertIn("completed / action_required", snapshot["body"])
        self.assertNotIn("EFFECT_ACK_DONE", snapshot["body"])
        self.assertNotIn("APPROVED", snapshot["body"])


class TestHumanMachineInterfaceAdaptation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.ai = ENTRYPOINT.read_text(encoding="utf-8")
        cls.boot = BOOTLOADER.read_text(encoding="utf-8")

    def test_reuse_before_create_and_fastest_verified_path(self):
        self.assertTrue(self.policy["reuse_before_create"])
        self.assertEqual(self.policy["adaptive_routing"]["strategy"], "FASTEST_VERIFIED_PATH")
        self.assertEqual(self.policy["adaptation_mode"], "MEASURE_CACHE_RANK_PROPOSE_REVIEW")

    def test_four_distinct_cache_layers_are_locked(self):
        ids = {row["id"] for row in self.policy["cache_layers"]}
        self.assertEqual(ids, {
            "L0_SESSION",
            "L1_PERSONAL_WORKING_MEMORY",
            "L2_RUNTIME_TOOLCHAIN",
            "L3_DERIVED_KNOWLEDGE",
        })

    def test_speed_may_not_reduce_quality_or_gates(self):
        selection = self.matrix["selection"]
        self.assertFalse(selection["quality_regression_allowed"])
        self.assertFalse(selection["mandatory_gate_reduction_allowed"])
        forbidden = set(self.policy["never_optimize_by"])
        self.assertIn("skipping mandatory gates", forbidden)
        self.assertIn("weakening exact-head binding", forbidden)
        self.assertIn("dropping provenance", forbidden)
        self.assertIn("treating cached output as proof authority", forbidden)

    def test_preference_requires_comparable_evidence(self):
        contract = self.policy["evaluation_matrix"]
        self.assertGreaterEqual(contract["minimum_observations_before_preference"], 3)
        self.assertTrue(contract["quality_must_not_regress"])
        self.assertEqual(self.matrix["selection"]["preferred_path"], "UNSET_UNTIL_COMPARABLE_EVIDENCE_EXISTS")

    def test_audio_and_incremental_processing_are_hash_bound(self):
        incremental = self.policy["incremental_processing"]
        self.assertTrue(incremental["prefer_changed_bytes_over_full_reprocessing"])
        self.assertTrue(incremental["content_addressed_chunks"])
        self.assertTrue(incremental["audio"]["transcript_key_includes_audio_sha256"])
        self.assertTrue(incremental["audio"]["cache_per_chunk_transcript"])

    def test_context_entrypoint_and_bootloader_bind_contract(self):
        adaptation = self.context["human_machine_interface_adaptation"]
        self.assertEqual(adaptation["policy"], "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json")
        self.assertEqual(adaptation["evaluation_matrix"], "state/interface_adaptation/EVALUATION_MATRIX.json")
        self.assertIn("policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json", self.context["required_read_order"])
        self.assertIn("state/interface_adaptation/EVALUATION_MATRIX.json", self.context["required_read_order"])
        self.assertIn("ADAPTIVE HUMAN-MACHINE INTERFACE", self.ai)
        self.assertIn("FASTEST_VERIFIED_PATH", self.ai)
        self.assertIn("load_interface_adaptation", self.boot)
        self.assertIn("INTERFACE_ADAPTATION_MODE", self.boot)

    def test_external_effects_and_secrets_remain_fail_closed(self):
        self.assertFalse(self.policy["privacy_and_security"]["secrets_in_cache"])
        self.assertFalse(self.policy["privacy_and_security"]["credentials_in_cache"])
        self.assertIn("performing external effects without authorization", self.policy["never_optimize_by"])
        self.assertFalse(self.policy["release_claims"]["PASS"])
        self.assertFalse(self.policy["release_claims"]["FINAL_PASS"])
        self.assertFalse(self.policy["release_claims"]["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--feedback-report":
        Path(sys.argv[2]).write_text(json.dumps(feedback_report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        unittest.main()
