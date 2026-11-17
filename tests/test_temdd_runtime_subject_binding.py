"""Exercise the actual shell guard and ledger argv without starting GUI services."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "deploy/universal-terminal/entrypoint.sh"
BEGIN = "# BEGIN TEMDD deployment subject binding"
END = "# END TEMDD deployment subject binding"


class TEMDDRuntimeSubjectBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ENTRYPOINT.read_text(encoding="utf-8")
        if cls.source.count(BEGIN) != 1 or cls.source.count(END) != 1:
            raise AssertionError("The tested subject guard must occur exactly once")
        cls.guard = cls.source.split(BEGIN, 1)[1].split(END, 1)[0]
        start = cls.source.index("python3 -B /opt/qikvrt/src/qikvrt_temdd_event_ledger.py serve")
        stop = cls.source.index("\n  >", start)
        cls.command = cls.source[start:stop].replace("\\\n", " ").rstrip()

    def invoke(self, variables):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("QIKVRT_")}
        env.update(variables)
        script = ('set -eu\n' + self.guard + '\n'
                  'HTTP_HOST=127.0.0.1\nHTTP_PORT=8771\nSTATE_DIR=/tmp/state\n'
                  'python3() { printf "%s\\n" "$@"; }\n' + self.command + '\n')
        return subprocess.run(["/bin/sh", "-c", script], env=env,
                              capture_output=True, text=True, timeout=5)

    def assert_subject(self, variables, expected, repository=None):
        result = self.invoke(variables)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = result.stdout.splitlines()
        self.assertIn("/opt/qikvrt/src/qikvrt_temdd_event_ledger.py", args)
        self.assertEqual(args.count("--pr"), int(expected is not None))
        if expected is not None:
            index = args.index("--pr")
            self.assertEqual(args[index:index + 2], ["--pr", expected])
        self.assertEqual(args.count("--repository"), int(repository is not None))
        if repository is not None:
            index = args.index("--repository")
            self.assertEqual(args[index:index + 2], ["--repository", repository])

    def test_unsealed_launch_requires_both_explicit_subject_fields(self):
        for variables, missing in (({}, 'QIKVRT_TEMDD_PR'),
                ({'QIKVRT_TEMDD_PR': '1124'}, 'QIKVRT_TEMDD_REPOSITORY'),
                ({'QIKVRT_TEMDD_REPOSITORY': 'ingolf-lohmann/qik-vrt'}, 'QIKVRT_TEMDD_PR')):
            with self.subTest(variables=variables):
                result = self.invoke(variables)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(missing, result.stderr)
                self.assertEqual(result.stdout, '')

    def test_explicit_pr_is_passed_as_two_arguments(self):
        self.assert_subject({"QIKVRT_TEMDD_PR": "1124",
                             "QIKVRT_TEMDD_REPOSITORY": "ingolf-lohmann/qik-vrt"},
                            "1124", "ingolf-lohmann/qik-vrt")

    def test_exact_head_requires_explicit_pr(self):
        result = self.invoke({"QIKVRT_EXACT_HEAD": "a" * 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("QIKVRT_TEMDD_PR", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_exact_tree_requires_explicit_pr(self):
        result = self.invoke({"QIKVRT_EXACT_TREE": "b" * 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("QIKVRT_TEMDD_PR", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_exact_subject_uses_configured_pr_not_legacy_default(self):
        self.assert_subject({"QIKVRT_EXACT_HEAD": "a" * 40,
                             "QIKVRT_EXACT_TREE": "b" * 40,
                             "QIKVRT_TEMDD_PR": "1124",
                             "QIKVRT_TEMDD_REPOSITORY": "ingolf-lohmann/qik-vrt"},
                            "1124", "ingolf-lohmann/qik-vrt")

    def test_exact_deployment_requires_explicit_repository(self):
        for bound in ("QIKVRT_EXACT_HEAD", "QIKVRT_EXACT_TREE"):
            with self.subTest(bound=bound):
                result = self.invoke({bound: "a" * 40, "QIKVRT_TEMDD_PR": "523"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("QIKVRT_TEMDD_REPOSITORY", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_explicit_repository_does_not_assume_authority_or_mirror(self):
        for repository in ("ingolf-lohmann/qik-vrt", "Goldkelch/qik-vrt"):
            with self.subTest(repository=repository):
                self.assert_subject({"QIKVRT_TEMDD_REPOSITORY": repository,
                                     "QIKVRT_TEMDD_PR": "1124"},
                                    "1124", repository)

    def test_invalid_repository_cannot_start_ledger(self):
        for value in ("", "owner", "/repo", "owner/", "a/b/c", "a b/c", "a/b;echo BAD",
                      "a/b\n", "https://github.com/owner/repo"):
            with self.subTest(value=value):
                result = self.invoke({"QIKVRT_TEMDD_REPOSITORY": value, "QIKVRT_TEMDD_PR": "1124"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("QIKVRT_TEMDD_REPOSITORY", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_invalid_pr_cannot_start_ledger(self):
        for value in ("", "0", "01124", "-1", "1124;echo BAD", " 1124", "1124\n", "abc"):
            with self.subTest(value=value):
                result = self.invoke({"QIKVRT_TEMDD_PR": value,
                                      "QIKVRT_TEMDD_REPOSITORY": "ingolf-lohmann/qik-vrt"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("QIKVRT_TEMDD_PR", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_guard_precedes_runtime_side_effects(self):
        self.assertLess(self.source.index(BEGIN), self.source.index("mkdir -p"))
        self.assertIn('"$@"', self.command)
        result = subprocess.run(["/bin/sh", "-n", str(ENTRYPOINT)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


class TerminalHealthBrowserBindingTests(unittest.TestCase):
    """Execute the health shell; external daemon/GUI commands are fixtures.

    The metadata validator runs in the actual Python interpreter. These tests
    prove admission behavior, not a native Firefox, SSE or deployed runtime.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.state = {
            "schema": "qikvrt_universal_terminal_runtime_state_v2",
            "runtime_id": "synthetic-health-fixture",
            "profile_persistent": True,
            "browser": "firefox-esr",
            "external_effect_claimed": False,
            "effect_ack_host": "127.0.0.1",
            "mesh_path": "/qik-vrt/mesh/v1/",
            "pass": False, "final_pass": False, "effect_ack_done": False,
        }
        commands = {
            "curl": 'exit "${HEALTH_HTTP_EXIT:-0}"\n',
            "pgrep": 'exit "${HEALTH_PROCESS_EXIT:-0}"\n',
            "xwininfo": 'if [ "${HEALTH_WINDOW_MISSING:-0}" = 0 ]; then '
                        'printf \'%s\\n\' \'"Navigator" "firefox"\'; fi\n',
            # Only the standalone SSE dependency check is simulated. The
            # runtime.json validator, including its argv binding, is real.
            "python3": 'if [ "$#" -eq 2 ]; then exit "${HEALTH_SSE_EXIT:-0}"; fi\n'
                       'exec "$HEALTH_PYTHON" "$@"\n',
        }
        for name, body in commands.items():
            path = self.bin / name
            path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
            path.chmod(0o700)

    def invoke(self, **variables):
        (self.work / "runtime.json").write_text(json.dumps(self.state), encoding="utf-8")
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("QIKVRT_", "HEALTH_"))}
        env.update(PATH=str(self.bin) + os.pathsep + env.get("PATH", ""),
                   QIKVRT_STATE_DIR=str(self.work), HEALTH_PYTHON=sys.executable)
        env.update(variables)
        return subprocess.run(["/bin/sh", str(ROOT / "deploy/universal-terminal/runtime-health.sh")],
                              env=env, capture_output=True, text=True, timeout=5)

    def test_default_browser_matches_default_terminal_start(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_override_matches_terminal_runtime_metadata(self):
        self.state["browser"] = "firefox"
        result = self.invoke(QIKVRT_FIREFOX_BINARY="firefox")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_and_release_cannot_accept_each_others_metadata(self):
        for configured, recorded in (("firefox", "firefox-esr"), ("firefox-esr", "firefox")):
            with self.subTest(configured=configured, recorded=recorded):
                self.state["browser"] = recorded
                result = self.invoke(QIKVRT_FIREFOX_BINARY=configured)
                self.assertNotEqual(result.returncode, 0)

    def test_browser_override_does_not_weaken_effect_boundary(self):
        self.state["browser"] = "firefox"
        for field in ("external_effect_claimed", "pass", "final_pass", "effect_ack_done"):
            with self.subTest(field=field):
                self.state[field] = True
                try:
                    result = self.invoke(QIKVRT_FIREFOX_BINARY="firefox")
                    self.assertNotEqual(result.returncode, 0)
                finally:
                    self.state[field] = False

    def test_browser_override_still_requires_each_runtime_dependency(self):
        self.state["browser"] = "firefox"
        for variable in ("HEALTH_HTTP_EXIT", "HEALTH_PROCESS_EXIT", "HEALTH_WINDOW_MISSING", "HEALTH_SSE_EXIT"):
            with self.subTest(variable=variable):
                result = self.invoke(QIKVRT_FIREFOX_BINARY="firefox", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

