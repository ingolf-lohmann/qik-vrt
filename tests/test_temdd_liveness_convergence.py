#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finite-lasso regressions for the unproved TEMDD convergence contract."""
from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class _LivenessLasso:
    """Test model: each state's outgoing step is followed by an explicit cycle."""

    states: tuple[dict[str, object], ...]
    loop_start: int

    def successor(self, position: int) -> int:
        return position + 1 if position + 1 < len(self.states) else self.loop_start

    def future(self, position: int) -> list[int]:
        visited: list[int] = []
        while position not in visited:
            visited.append(position)
            position = self.successor(position)
        return visited

    def evaluate(self, formula: object, position: int = 0) -> bool:
        """Evaluate the JSON temporal AST on the whole ultimately periodic run.

        This is a test-only finite-model oracle, not a runtime proof evaluator.
        No expression from the contract is executed as Python code.
        """
        if isinstance(formula, str):
            if formula not in {"Goal", "ProductiveStep", "ExplicitExternalHold"}:
                raise ValueError(f"unknown temporal atom: {formula}")
            return self.states[position][formula] is True
        if not isinstance(formula, dict) or len(formula) != 1:
            raise ValueError("temporal formula must have exactly one operator")
        operator, argument = next(iter(formula.items()))
        if operator == "not":
            return not self.evaluate(argument, position)
        if operator in {"G", "F"}:
            values = [self.evaluate(argument, i) for i in self.future(position)]
            return all(values) if operator == "G" else any(values)
        if operator in {"and", "or", "implies"}:
            if not isinstance(argument, list) or not argument:
                raise ValueError("boolean operator requires a nonempty array")
            values = [self.evaluate(item, position) for item in argument]
            if operator == "implies":
                if len(values) != 2:
                    raise ValueError("implication requires two operands")
                return not values[0] or values[1]
            return all(values) if operator == "and" else any(values)
        raise ValueError(f"unknown temporal operator: {operator}")


def _liveness_state(*, rank: int, goal: bool = False, hold: bool = False,
                    productive: bool = False) -> dict[str, object]:
    return {"rank": rank, "Goal": goal, "ExplicitExternalHold": hold,
            "ProductiveStep": productive}


class TemddLivenessConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.contract = json.loads((cls.root / "state/autonomy/"
                                  "TEMDD_LIVENESS_CONVERGENCE_CONTRACT_V1.json")
                                 .read_text(encoding="utf-8"))

    def premises(self, run: _LivenessLasso) -> dict[str, bool]:
        # Fixtures grant Safety, scheduler fairness and a fixed environment.
        # In an absorbing HOLD no productive action is enabled, so scheduler
        # fairness is vacuous. External release is checked independently.
        c = self.contract
        outside_goal = [i for i, state in enumerate(run.states)
                        if not state["Goal"]]
        values = {
            "Safety": True,
            "ProductiveLiveness": run.evaluate(c["liveness"]["formula"]),
            "ExternalHoldRelease": run.evaluate(c["external_hold"]["release_formula"]),
            "WellFounded(V)": all(type(s["rank"]) is int and s["rank"] >= 0
                                 for s in run.states),  # concrete natural rank
            "NonIncreaseOnEveryNonGoalStep(V)": all(
                run.states[run.successor(i)]["rank"] <= run.states[i]["rank"]
                for i in outside_goal),
            "StrictDecreaseOnEveryInternalProductiveStep(V)": all(
                run.states[run.successor(i)]["rank"] < run.states[i]["rank"]
                for i in outside_goal if run.states[i]["ProductiveStep"]),
            "FairExecution": True,
            "StableRequiredEnvironmentAssumptions": True,
        }
        return {name: values[name] for name in c["theorem"]["premises"]}

    def test_permanent_hold_is_not_a_goal_reachability_witness(self) -> None:
        # The self-loop specifies an infinite absorbing HOLD, not a timeout.
        run = _LivenessLasso((_liveness_state(rank=1, hold=True),), 0)
        self.assertTrue(run.evaluate(self.contract["diagnostic_response"]["formula"]))
        self.assertFalse(run.evaluate("Goal"))
        premises = self.premises(run)
        self.assertFalse(premises["ProductiveLiveness"])
        self.assertFalse(premises["ExternalHoldRelease"])
        self.assertFalse(all(premises.values()), "HOLD must not prove GoalReachability")

    def test_original_hold_disjunction_admits_a_counterexample(self) -> None:
        run = _LivenessLasso((_liveness_state(rank=1, hold=True),), 0)
        legacy = self.premises(run)
        legacy.pop("ProductiveLiveness")
        legacy.pop("ExternalHoldRelease")
        legacy.pop("NonIncreaseOnEveryNonGoalStep(V)")
        legacy["Liveness"] = run.evaluate(self.contract["diagnostic_response"]["formula"])
        self.assertTrue(all(legacy.values()))
        self.assertFalse(run.evaluate({"F": "Goal"}))

    def test_released_hold_followed_by_progress_reaches_goal(self) -> None:
        run = _LivenessLasso((
            _liveness_state(rank=1, hold=True),
            _liveness_state(rank=1, productive=True),
            _liveness_state(rank=0, goal=True),
        ), 2)
        self.assertTrue(all(self.premises(run).values()))
        self.assertTrue(run.evaluate({"F": "Goal"}))

    def test_release_and_decrease_cannot_hide_rank_reset_cycle(self) -> None:
        run = _LivenessLasso((
            _liveness_state(rank=0, hold=True),
            _liveness_state(rank=1, productive=True),
        ), 0)
        premises = self.premises(run)
        self.assertTrue(premises["ProductiveLiveness"])
        self.assertTrue(premises["ExternalHoldRelease"])
        self.assertTrue(premises["StrictDecreaseOnEveryInternalProductiveStep(V)"])
        self.assertFalse(premises["NonIncreaseOnEveryNonGoalStep(V)"])
        self.assertFalse(all(premises.values()))
        self.assertFalse(run.evaluate({"F": "Goal"}))

    def test_finite_non_goal_stop_is_checked_as_stuttering_deadlock(self) -> None:
        run = _LivenessLasso((_liveness_state(rank=0),), 0)
        self.assertFalse(self.premises(run)["ProductiveLiveness"])
        self.assertFalse(run.evaluate({"F": "Goal"}))

    def test_progress_before_a_permanent_hold_does_not_discharge_liveness(self) -> None:
        run = _LivenessLasso((
            _liveness_state(rank=1, productive=True),
            _liveness_state(rank=0, hold=True),
        ), 1)
        self.assertFalse(self.premises(run)["ProductiveLiveness"])
        self.assertFalse(self.premises(run)["ExternalHoldRelease"])

    def test_contract_and_markdown_preserve_theorem_and_evidence_boundaries(self) -> None:
        c = self.contract
        self.assertEqual(c["theorem"]["claim"], " AND ".join(c["theorem"]["premises"])
                         + " IMPLIES " + c["theorem"]["conclusion"])
        self.assertEqual(c["TEMDD_LIVENESS_CONVERGENCE_THEOREM"], "UNPROVED")
        self.assertFalse(c["theorem"]["proved"])
        self.assertFalse(c["acceptance"]["effect_ack_done"])
        self.assertFalse(c["predecessor_evidence_transfer"])
        self.assertFalse(c["diagnostic_response"]["goal_reachability_premise"])
        self.assertEqual(c["temporal_semantics"]["bounded_hold_observation_future"], "UNKNOWN")
        for filename in ("TEMDD_LIVENESS_CONVERGENCE_CONTRACT_V1.md",
                         "WHY_TEMDD_LIVENESS_MATTERS.md"):
            text = (self.root / "research/temdd" / filename).read_text(encoding="utf-8")
            for premise in c["theorem"]["premises"]:
                self.assertIn(premise, text)
            for marker in ("TEMDD_LIVENESS_CONVERGENCE_THEOREM = UNPROVED",
                           "EFFECT_ACK_DONE = FALSE", "PREDECESSOR_EVIDENCE_TRANSFER = FALSE"):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
