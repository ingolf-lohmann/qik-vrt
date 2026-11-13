"""Read-only, bounded GitHub CI failure diagnosis for EMP/TEMDD.

Only accepts an explicitly supplied workflow run id and trusted repository.
Never mutates GitHub or claims to have repaired a failure.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def inspect(run_id: int, token: str, max_pages: int = 10) -> dict:
    if not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("invalid run id")
    if not token:
        raise ValueError("missing GitHub token")
    failed = []
    inspected = 0
    truncated = False
    for page in range(1, max_pages + 1):
        url = ("https://api.github.com/repos/ingolf-lohmann/qik-vrt/"
               f"actions/runs/{run_id}/jobs?per_page=100&page={page}")
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-emp-readonly"})
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.load(response)
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("missing jobs array")
        inspected += len(jobs)
        for job in jobs:
            if job.get("conclusion") in ("failure", "timed_out", "action_required"):
                failed.append({
                    "job_id": job.get("id"), "name": job.get("name"),
                    "conclusion": job.get("conclusion"),
                    "url": job.get("html_url"),
                    "failed_steps": [
                        {"name": s.get("name"), "conclusion": s.get("conclusion")}
                        for s in job.get("steps", [])
                        if s.get("conclusion") == "failure"]})
        if len(jobs) < 100:
            break
    else:
        truncated = True
    return {"run_id": run_id, "jobs_inspected": inspected,
            "failed_jobs": failed, "pagination_truncated": truncated,
            "temdd_required": bool(failed) or truncated,
            "effect_ack_done": False, "repair_executed": False}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m runtime.emp.ci_diagnose RUN_ID OUTPUT")
    result = inspect(int(sys.argv[1]), os.environ.get("GITHUB_TOKEN", ""))
    with open(sys.argv[2], "w", encoding="utf-8") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
