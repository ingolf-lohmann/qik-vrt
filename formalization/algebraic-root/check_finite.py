#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-ND-4.0
# Copyright (c) 2026 Ingolf Lohmann.
import itertools
import json

B = (False, True)
add = lambda a, b: a and b
mul = lambda a, b: a != b
zero, one = True, False
assert zero != one
for a in B:
    assert add(a, zero) == a == add(zero, a)
    assert mul(a, one) == a == mul(one, a)
witnesses = []
for a, b, c in itertools.product(B, repeat=3):
    lhs = mul(a, add(b, c))
    rhs = add(mul(a, b), mul(a, c))
    if lhs != rhs:
        witnesses.append([a, b, c])
assert [True, False, True] in witnesses
print(json.dumps({"scope": "finite-exhaustive-not-kernel-proof",
                  "cases": 8, "counterexamples": witnesses,
                  "identity_cases": 2, "status": "PASS"}, sort_keys=True))
