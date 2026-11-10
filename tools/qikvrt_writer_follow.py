"""Strict same-writer successor chain verification.

Consume machine-readable GitHub job log text; never infer a successful
mutation from an in-progress job or an unverified push message.
"""
import re
from dataclasses import dataclass
from typing import Tuple

SHA = r"[0-9a-f]{40}"
SUBJECT = re.compile(rf"QIKVRT_REENTRY_SUBJECT iteration=(\d+) head=({SHA}) tree=({SHA})")
SUCCESSOR = re.compile(
    rf"QIKVRT_SUCCESSOR_REENTRY iteration=(\d+) predecessor=({SHA}) "
    rf"successor=({SHA}) successor_tree=({SHA}) readback_head=({SHA}) readback_tree=({SHA})"
)
FIXPOINT = re.compile(rf"QIKVRT_FIXPOINT_REACHED iteration=(\d+) head=({SHA}) tree=({SHA})")


@dataclass(frozen=True)
class Chain:
    initial_head: str
    latest_head: str
    latest_tree: str
    successor_count: int
    fixpoint_reached: bool
    errors: Tuple[str, ...]


def verify_chain(log: str, expected_head: str) -> Chain:
    """Validate order, CAS predecessor continuity and exact readback equality."""
    errors = []
    if not re.fullmatch(SHA, expected_head):
        errors.append("invalid expected HEAD")
    latest = expected_head
    tree = ""
    count = 0
    fixed = False
    for line in log.splitlines():
        # GitHub Actions timestamps may precede the event marker.
        m = SUBJECT.search(line)
        if m:
            if m.group(2) != latest:
                errors.append("subject HEAD diverges from writer chain")
            tree = m.group(3)
        m = SUCCESSOR.search(line)
        if m:
            iteration, predecessor, successor, successor_tree, readback_head, readback_tree = m.groups()
            if predecessor != latest:
                errors.append("predecessor mismatch")
            if successor != readback_head or successor_tree != readback_tree:
                errors.append("independent readback mismatch")
            if successor == predecessor:
                errors.append("successor did not advance HEAD")
            latest, tree = successor, successor_tree
            count += 1
        m = FIXPOINT.search(line)
        if m:
            if m.group(2) != latest:
                errors.append("fixpoint HEAD mismatch")
            if tree and m.group(3) != tree:
                errors.append("fixpoint TREE mismatch")
            fixed = True
    return Chain(expected_head, latest, tree, count, fixed and not errors, tuple(errors))
