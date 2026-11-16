"""Repository-owned EMP work decomposition, deterministic and fail-closed.

The repository, not a conversational client, owns the task graph. This planner
never claims execution, approval or EAP acknowledgement. Executors consume only
eligible actions and persist outcomes in the EMP journal.
"""
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Step:
    key: str
    dependencies: tuple[str, ...] = ()
    effectful: bool = False


STEPS = (
    Step("observe"),
    Step("diagnose", ("observe",)),
    Step("temdd_repair", ("diagnose",), True),
    Step("exact_head_ci", ("temdd_repair",)),
    Step("governance", ("exact_head_ci",)),
    Step("fenced_writer", ("governance",), True),
    Step("independent_eap_readback", ("fenced_writer",)),
    Step("release_admission", ("independent_eap_readback",)),
)


def plan(completed: Iterable[str], *, authorized: bool,
         writer_admitted: bool, external_blocks: Iterable[str] = ()) -> dict:
    done = set(completed)
    keys = {s.key for s in STEPS}
    if not done <= keys:
        raise ValueError("unknown completed steps")
    blockers = sorted(set(external_blocks))
    ready = []
    held = []
    for step in STEPS:
        if step.key in done:
            continue
        missing = sorted(set(step.dependencies) - done)
        if missing:
            held.append({"step": step.key, "reason": "dependencies", "missing": missing})
        elif blockers:
            held.append({"step": step.key, "reason": "external_blocker", "blocks": blockers})
        elif step.effectful and (not authorized or not writer_admitted):
            held.append({"step": step.key, "reason": "effect_admission_required"})
        else:
            ready.append(step.key)
    return {
        "schema": "qikvrt_emp_repository_plan_v1",
        "ready": ready, "held": held,
        "done": sorted(done),
        "verified": len(done) == len(STEPS),
        "effect_ack_done": False,  # never infer global EAP ACK from a plan
    }
