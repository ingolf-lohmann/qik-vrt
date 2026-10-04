# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finite static undirected maze: exploration and separately checked certificates.

This is a model reference, not a declaration of production QIK-VRT conformance.
The explorer sees only an exhaustive local neighbour oracle and side labels.
"""
from collections import deque


def portal_id(a, b):
    return (min(a, b), max(a, b))


def classify(portals, complete=False):
    n = len({portal_id(a, b) for a, b in portals})
    if n >= 2:
        return "MORE_THAN_ONE"
    if complete:
        return "ZERO" if n == 0 else "EXACTLY_ONE"
    return "UNDETERMINED" if n == 0 else "AT_LEAST_ONE"


def snapshot_graph(graph):
    """Validate the mathematical input assumptions without inventing missing edges."""
    result = {}
    for vertex, neighbours in graph.items():
        if type(vertex) is not int:
            raise ValueError("stable integer vertex identities required")
        neighbours = tuple(neighbours)
        if any(type(n) is not int for n in neighbours):
            raise ValueError("stable integer neighbour identities required")
        if len(set(neighbours)) != len(neighbours) or vertex in neighbours:
            raise ValueError("simple graph required; duplicates and self-loops excluded")
        result[vertex] = tuple(sorted(neighbours))
    for vertex, neighbours in result.items():
        if any(n not in result or vertex not in result[n] for n in neighbours):
            raise ValueError("closed symmetric adjacency snapshot required")
    return result


def explore(neighbours, is_inside, start):
    """Explore C(start); each discovered vertex is expanded exactly once.

    Termination is conditional on the oracle's finite, static, exhaustive model.
    No global-completion assertion is made from one reachable component.
    """
    pending = deque([start])
    discovered = {start}
    rows = {}
    portals = set()
    inspected = set()
    while pending:
        vertex = pending.popleft()
        row = tuple(sorted(neighbours(vertex)))
        rows[vertex] = row
        side = is_inside(vertex)
        if type(side) is not bool:
            raise ValueError("inside/outside must be boolean")
        for other in row:
            other_side = is_inside(other)
            if type(other_side) is not bool:
                raise ValueError("inside/outside must be boolean")
            edge = portal_id(vertex, other)
            inspected.add(edge)
            if side != other_side:
                portals.add(edge)
            if other not in discovered:
                discovered.add(other)
                pending.append(other)
    return {
        "schema": "qikvrt_labyrinth_certificate_v1",
        "start": start,
        "expanded_rows": [[v, list(rows[v])] for v in sorted(rows)],
        "inspected_edges": [list(e) for e in sorted(inspected)],
        "portals": [list(e) for e in sorted(portals)],
        "classification": classify(portals, complete=True),
        "scope": "REACHABLE_COMPONENT_ONLY",
    }


def verify_certificate(graph, inside, certificate, require_global=False):
    """Check a certificate against a separate authoritative graph snapshot.

    Uses Boolean transitive closure, not the explorer's queue implementation.
    Source-oracle accuracy is an explicit assumption, not proved by this check.
    """
    graph = snapshot_graph(graph)
    if set(inside) != set(graph) or any(type(v) is not bool for v in inside.values()):
        raise ValueError("complete boolean partition required")
    start = certificate["start"]
    if start not in graph:
        raise ValueError("start outside snapshot")
    expected_keys = {"schema", "start", "expanded_rows", "inspected_edges",
                     "portals", "classification", "scope"}
    if set(certificate) != expected_keys or certificate["schema"] != "qikvrt_labyrinth_certificate_v1":
        raise ValueError("certificate schema mismatch")
    rows = certificate["expanded_rows"]
    if len({v for v, _ in rows}) != len(rows):
        raise ValueError("duplicate expansion row")
    vertices = sorted(graph)
    reach = {(a, b): a == b or b in graph[a] for a in vertices for b in vertices}
    for k in vertices:
        for a in vertices:
            for b in vertices:
                reach[a, b] = reach[a, b] or (reach[a, k] and reach[k, b])
    component = {v for v in vertices if reach[start, v]}
    if {v for v, _ in rows} != component:
        raise ValueError("expanded rows do not equal reachable component")
    if any(tuple(row) != graph[v] for v, row in rows):
        raise ValueError("adjacency differs from authoritative snapshot")
    expected_edges = {(a, b) for a in component for b in graph[a] if a < b}
    expected_portals = {(a, b) for a, b in expected_edges if inside[a] != inside[b]}
    if certificate["inspected_edges"] != [list(e) for e in sorted(expected_edges)]:
        raise ValueError("edge coverage mismatch")
    if certificate["portals"] != [list(e) for e in sorted(expected_portals)]:
        raise ValueError("portal identity or coverage mismatch")
    n = len(expected_portals)
    expected_class = "ZERO" if n == 0 else "EXACTLY_ONE" if n == 1 else "MORE_THAN_ONE"
    if certificate["classification"] != expected_class:
        raise ValueError("classification mismatch")
    if certificate["scope"] != "REACHABLE_COMPONENT_ONLY":
        raise ValueError("unsupported scope assertion")
    global_complete = component == set(vertices)
    if require_global and not global_complete:
        raise ValueError("unreachable components prevent a global claim")
    return {"certificate_valid": True, "global_complete": global_complete,
            "vertices": len(component), "edges": len(expected_edges),
            "portal_count": n, "classification": expected_class}
