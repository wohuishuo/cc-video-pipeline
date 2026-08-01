from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.contracts import ContractError, GraphDefinition  # noqa: E402
from studio.graph import validate_graph  # noqa: E402


PREPARED_FOLDER_GRAPH = {
    "schemaVersion": 1,
    "graphId": "prepared-folder-edge",
    "revision": 1,
    "nodes": [
        {"id": "verify", "type": "verify-output", "config": {}},
        {"id": "source", "type": "prepared-folder", "config": {}},
        {"id": "localize", "type": "edge-localize", "config": {}},
    ],
    "edges": [
        {"source": "source", "target": "localize", "relationship": "Fact"},
        {"source": "localize", "target": "verify", "relationship": "Fact"},
    ],
}


def test_graph_validation_returns_deterministic_topological_order():
    graph = GraphDefinition.from_dict(PREPARED_FOLDER_GRAPH)
    assert validate_graph(graph) == ("source", "localize", "verify")


def test_graph_fingerprint_is_independent_of_input_key_order():
    first = GraphDefinition.from_dict(PREPARED_FOLDER_GRAPH)
    reordered = {
        "revision": 1,
        "nodes": PREPARED_FOLDER_GRAPH["nodes"],
        "graphId": "prepared-folder-edge",
        "edges": PREPARED_FOLDER_GRAPH["edges"],
        "schemaVersion": 1,
    }
    assert GraphDefinition.from_dict(reordered).fingerprint == first.fingerprint


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda value: value["nodes"].append(
                {"id": "source", "type": "prepared-folder", "config": {}}
            ),
            "DUPLICATE_NODE",
        ),
        (
            lambda value: value["edges"].append(
                {"source": "missing", "target": "verify", "relationship": "Fact"}
            ),
            "UNKNOWN_ENDPOINT",
        ),
        (
            lambda value: value["edges"].append(
                {"source": "verify", "target": "source", "relationship": "Command"}
            ),
            "GRAPH_CYCLE",
        ),
    ],
)
def test_graph_rejects_invalid_structure(mutate, code):
    import copy

    value = copy.deepcopy(PREPARED_FOLDER_GRAPH)
    mutate(value)
    with pytest.raises(ContractError) as raised:
        validate_graph(GraphDefinition.from_dict(value))
    assert raised.value.code == code

