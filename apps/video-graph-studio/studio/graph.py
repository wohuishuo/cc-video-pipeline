"""Directed acyclic graph validation."""

from __future__ import annotations

import heapq

from .contracts import ContractError, GraphDefinition


def validate_graph(graph: GraphDefinition) -> tuple[str, ...]:
    incoming = {node.id: 0 for node in graph.nodes}
    outgoing: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        incoming[edge.target] += 1
        outgoing[edge.source].append(edge.target)

    ready = [identifier for identifier, count in incoming.items() if count == 0]
    heapq.heapify(ready)
    ordered: list[str] = []
    while ready:
        identifier = heapq.heappop(ready)
        ordered.append(identifier)
        for target in sorted(outgoing[identifier]):
            incoming[target] -= 1
            if incoming[target] == 0:
                heapq.heappush(ready, target)
    if len(ordered) != len(graph.nodes):
        raise ContractError("GRAPH_CYCLE", "graph must be acyclic")
    return tuple(ordered)

