"""Versioned immutable contracts for workflow graphs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


RELATIONSHIP_TYPES = frozenset(
    {"Command", "Query", "Fact", "Policy", "Strategy", "Factory", "Adapter", "Projection"}
)


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "config": self.config}


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relationship: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
        }


@dataclass(frozen=True)
class GraphDefinition:
    schema_version: int
    graph_id: str
    revision: int
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GraphDefinition":
        try:
            nodes = tuple(
                GraphNode(str(row["id"]), str(row["type"]), dict(row.get("config", {})))
                for row in value["nodes"]
            )
            edges = tuple(
                GraphEdge(str(row["source"]), str(row["target"]), str(row["relationship"]))
                for row in value["edges"]
            )
            graph = cls(
                schema_version=int(value["schemaVersion"]),
                graph_id=str(value["graphId"]),
                revision=int(value["revision"]),
                nodes=nodes,
                edges=edges,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError("MALFORMED_GRAPH", f"invalid graph definition: {error}") from error
        graph._validate_shape()
        return graph

    def _validate_shape(self) -> None:
        if self.schema_version != 1 or self.revision < 1 or not self.graph_id.strip():
            raise ContractError("MALFORMED_GRAPH", "unsupported schema or invalid identity")
        identifiers = [node.id for node in self.nodes]
        if any(not identifier.strip() for identifier in identifiers):
            raise ContractError("MALFORMED_GRAPH", "node IDs must not be empty")
        if len(set(identifiers)) != len(identifiers):
            raise ContractError("DUPLICATE_NODE", "node IDs must be unique")
        known = set(identifiers)
        for edge in self.edges:
            if edge.relationship not in RELATIONSHIP_TYPES:
                raise ContractError("UNKNOWN_RELATIONSHIP", edge.relationship)
            if edge.source not in known or edge.target not in known:
                raise ContractError("UNKNOWN_ENDPOINT", f"{edge.source}->{edge.target}")
            if edge.source == edge.target:
                raise ContractError("GRAPH_CYCLE", f"self edge at {edge.source}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "graphId": self.graph_id,
            "revision": self.revision,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()

