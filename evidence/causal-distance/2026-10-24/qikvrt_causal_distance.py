# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Read-only distances on a finite, explicitly scoped dependency graph.

Hash verification binds evidence bytes, not their truth. Admission of a causal
interpretation remains the caller's separate proof obligation. Never derive an
edge from ledger sequence, wall-clock order, or shared ancestry alone.
"""
from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf
from types import MappingProxyType
import unicodedata
from qikvrt_effect_ack import canonical_json, sha256_identifier


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    weight: int
    evidence_ref: str


class DependencyGraph:
    """Positive integer weights; one fixed subject, resolution and evidence scope.

    directed() is an extended quasi-metric. metric() is an extended metric on
    the undirected projection and a finite metric within each weak component.
    A metric path may traverse dependencies backwards and confers no influence.
    """
    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            raise AttributeError('IMMUTABLE_GRAPH_SNAPSHOT')
        object.__setattr__(self, name, value)

    def __init__(self, vertices, edges, evidence, *, subject_ref, resolution, scope):
        raw = tuple(vertices)
        if not raw or any(not isinstance(v, str) or not v.strip() for v in raw):
            raise ValueError('NONEMPTY_VERTEX_IDENTITIES_REQUIRED')
        if len(set(raw)) != len(raw):
            raise ValueError('DUPLICATE_VERTEX')
        if any(unicodedata.normalize('NFC', v) != v for v in raw):
            raise ValueError('NFC_VERTEX_IDENTITIES_REQUIRED')
        if any(not isinstance(s, str) or not s.strip() for s in (resolution, scope)):
            raise ValueError('RESOLUTION_AND_SCOPE_REQUIRED')
        if subject_ref not in evidence:
            raise ValueError('SUBJECT_EVIDENCE_REQUIRED')
        if sha256_identifier(evidence[subject_ref]) != subject_ref:
            raise ValueError('SUBJECT_HASH_MISMATCH')
        self.vertices = tuple(sorted(raw))
        self.edges = tuple(sorted(tuple(edges), key=lambda e: (e.source, e.target, e.weight, e.evidence_ref)))
        seen = set()
        for e in self.edges:
            if e.source not in raw or e.target not in raw or e.source == e.target:
                raise ValueError('INVALID_EDGE_ENDPOINT')
            if type(e.weight) is not int or e.weight <= 0:
                raise ValueError('POSITIVE_INTEGER_WEIGHT_REQUIRED')
            if (e.source, e.target) in seen:
                raise ValueError('DUPLICATE_EDGE')
            seen.add((e.source, e.target))
            if e.evidence_ref not in evidence:
                raise ValueError('EDGE_EVIDENCE_REQUIRED')
            data = evidence[e.evidence_ref]
            if sha256_identifier(data) != e.evidence_ref:
                raise ValueError('EDGE_HASH_MISMATCH')
            import json
            receipt = json.loads(data)
            if not isinstance(receipt, dict) or type(receipt.get('weight')) is not int:
                raise ValueError('TYPED_EDGE_RECEIPT_REQUIRED')
            expected = {'source': e.source, 'target': e.target, 'weight': e.weight,
                        'subject_ref': subject_ref, 'resolution': resolution, 'scope': scope}
            if any(receipt.get(k) != v for k, v in expected.items()):
                raise ValueError('EDGE_RECEIPT_BINDING_MISMATCH')
        forward = {v: [] for v in raw}
        undirected = {v: [] for v in raw}
        for e in self.edges:
            forward[e.source].append((e.target, e.weight))
            undirected[e.source].append((e.target, e.weight))
            undirected[e.target].append((e.source, e.weight))
        self._forward = MappingProxyType({v: tuple(sorted(a)) for v, a in forward.items()})
        self._undirected = MappingProxyType({v: tuple(sorted(a)) for v, a in undirected.items()})
        self.subject_ref, self.resolution, self.scope = subject_ref, resolution, scope
        self.graph_ref = sha256_identifier(canonical_json({
            'vertices': self.vertices, 'edges': [
                {'source': e.source, 'target': e.target, 'weight': e.weight,
                 'evidence_ref': e.evidence_ref} for e in self.edges],
            'subject_ref': subject_ref, 'resolution': resolution, 'scope': scope
        }).encode())
        self._sealed = True

    def _path(self, a, b, adjacency):
        if a not in adjacency or b not in adjacency:
            raise ValueError('UNKNOWN_VERTEX')
        queue = [(0, (a,))]
        best = {a: 0}
        while queue:
            cost, path = heappop(queue)
            node = path[-1]
            if cost != best[node]:
                continue
            if node == b:
                return cost, path
            for nxt, weight in adjacency[node]:
                value = cost + weight
                if value < best.get(nxt, inf):
                    best[nxt] = value
                    heappush(queue, (value, path + (nxt,)))
        return inf, ()

    def directed(self, a, b):
        return self._path(a, b, self._forward)[0]

    def metric(self, a, b):
        return self._path(a, b, self._undirected)[0]

    def query(self, a, b, *, structural=False):
        d, path = self._path(a, b, self._undirected if structural else self._forward)
        return {'graph_ref': self.graph_ref, 'subject_ref': self.subject_ref,
                'resolution': self.resolution, 'scope': self.scope,
                'measure': 'SYMMETRIC_STRUCTURAL_METRIC' if structural else 'DIRECTED_DEPENDENCY_DISTANCE',
                'source': a, 'target': b, 'distance': None if d == inf else d,
                'unit': 'declared_dependency_units', 'path': list(path),
                'status': 'NO_PATH_IN_BOUND_GRAPH' if d == inf else 'PATH_IN_BOUND_GRAPH',
                'physical_impossibility_inferred': False,
                'backwards_physical_influence_inferred': False}
