import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import validate as v  # noqa: E402

G = v.load_yaml(v.GRAPH)


def test_real_graph_is_valid():
    assert v.graph_errors(G) == []


def test_real_items_are_valid():
    errs, _ = v.item_errors(G)
    assert errs == []


def test_detects_prereq_cycle():
    g = copy.deepcopy(G)
    g["edges"].append({"from": "verb.transitivity", "to": "verb.inflection"})
    assert any("prereq cycle" in e for e in v.graph_errors(g))


def test_related_edge_does_not_count_as_cycle():
    g = copy.deepcopy(G)
    g["edges"].append({"from": "verbal.to_inf", "to": "noun.pronoun_it", "type": "related"})
    assert v.graph_errors(g) == []


def test_detects_unknown_node():
    g = copy.deepcopy(G)
    g["edges"].append({"from": "verb.tense", "to": "verb.nope"})
    assert any("unknown node" in e for e in v.graph_errors(g))


def test_detects_unreachable_node():
    g = copy.deepcopy(G)
    g["nodes"].append({"id": "orphan.node", "label": "x", "branch": "x", "weight": "low"})
    assert any("unreachable" in e for e in v.graph_errors(g))


def test_tag_edge_must_target_tag_node():
    g = copy.deepcopy(G)
    g["edges"].append({"from": "solve.stage", "to": "verb.tense", "type": "tag"})
    assert any("not kind=tag" in e for e in v.graph_errors(g))


def test_proto1_scope_is_verb_chain():
    p1 = {n["id"] for n in G["nodes"] if n.get("milestone") == "proto1"}
    assert p1 == {"verb.inflection", "verb.tense", "verb.transitivity"}
