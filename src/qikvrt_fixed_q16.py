# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Integer oracle for the portable C90 Q16.16 arithmetic contract.

This module does not quantize an arbitrary real number or authorize an effect.
Inputs and outputs are already scaled integer values.
"""

MIN_RAW = -(1 << 31)
MAX_RAW = (1 << 31) - 1
SCALE = 1 << 16


def _raw(value: int) -> int:
    if type(value) is not int:
        raise TypeError("Q16.16 requires an integer raw value")
    if not MIN_RAW <= value <= MAX_RAW:
        raise OverflowError("Q16.16 raw value out of range")
    return value


def add(a: int, b: int) -> int:
    return _raw(_raw(a) + _raw(b))


def mul(a: int, b: int) -> int:
    product = _raw(a) * _raw(b)
    magnitude = abs(product) // SCALE
    return _raw(-magnitude if product < 0 else magnitude)
