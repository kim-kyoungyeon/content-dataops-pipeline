#!/usr/bin/env python3
"""Structural validation for the grammar graph and items.

Checks what a machine can check. Whether the pedagogy is right
(e.g. a hidden conceptual cycle) is domain review, done by a person.

usage:
  python tools/validate.py            # validate, exit 1 on error
  python tools/validate.py --mermaid  # also regenerate docs/roadmap.md
  python tools/validate.py --check    # fail if docs/roadmap.md is stale
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "graph" / "grammar.yaml"
ITEMS_DIR = ROOT / "items"
ROADMAP = ROOT / "docs" / "roadmap.md"
ROOT_NODE = "base.terms"


def load_yaml(p: Path):
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def schema_errors(data, schema_name: str) -> list[str]:
    schema = json.loads((ROOT / "schema" / schema_name).read_text(encoding="utf-8"))
    v = Draft202012Validator(schema)
    return [f"schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(data), key=lambda e: list(e.path))]


def find_cycle(nodes: list[str], adj: dict[str, list[str]]) -> list[str] | None:
    """Return one cycle path if any (DFS with colors)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    parent: dict[str, str] = {}

    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, []):
            if color[v] == GRAY:
                path, x = [v], u
                while x != v:
                    path.append(x)
                    x = parent[x]
                path.append(v)
                return path[::-1]
            if color[v] == WHITE:
                parent[v] = u
                r = dfs(v)
                if r:
                    return r
        color[u] = BLACK
        return None

    for n in nodes:
        if color[n] == WHITE:
            r = dfs(n)
            if r:
                return r
    return None


def graph_errors(g: dict) -> list[str]:
    errs = schema_errors(g, "graph.schema.json")
    if errs:
        return errs  # structure broken, skip the rest

    ids = [n["id"] for n in g["nodes"]]
    dup = {i for i in ids if ids.count(i) > 1}
    errs += [f"duplicate node id: {i}" for i in sorted(dup)]

    node = {n["id"]: n for n in g["nodes"]}
    is_tag = {i: node[i].get("kind", "concept") == "tag" for i in node}
    prereq: dict[str, list[str]] = defaultdict(list)
    seen = set()

    for e in g["edges"]:
        a, b, t = e["from"], e["to"], e.get("type", "prereq")
        for end in (a, b):
            if end not in node:
                errs.append(f"edge {a}->{b}: unknown node '{end}'")
        if a == b:
            errs.append(f"self loop: {a}")
        key = (a, b, t)
        if key in seen:
            errs.append(f"duplicate edge: {a}->{b} ({t})")
        seen.add(key)
        if a in node and b in node:
            if t == "tag" and not is_tag[b]:
                errs.append(f"tag edge {a}->{b}: target is not kind=tag")
            if t != "tag" and is_tag[b]:
                errs.append(f"edge {a}->{b}: tag node used as {t}")
            if t == "prereq":
                prereq[a].append(b)

    if errs:
        return errs

    cyc = find_cycle(list(node), prereq)
    if cyc:
        errs.append("prereq cycle: " + " -> ".join(cyc))

    # every concept node must be reachable from the root via prereq edges
    if ROOT_NODE not in node:
        errs.append(f"root node missing: {ROOT_NODE}")
    else:
        reach, q = {ROOT_NODE}, deque([ROOT_NODE])
        while q:
            for v in prereq.get(q.popleft(), []):
                if v not in reach:
                    reach.add(v)
                    q.append(v)
        for i in ids:
            if not is_tag[i] and i not in reach:
                errs.append(f"unreachable from {ROOT_NODE}: {i}")
    return errs


def item_errors(g: dict) -> tuple[list[str], dict]:
    node = {n["id"]: n for n in g["nodes"]}
    errs, seen = [], set()
    stats = defaultdict(lambda: {"total": 0, "approved": 0, "pending": 0})
    for p in sorted(ITEMS_DIR.glob("*.yaml")):
        data = load_yaml(p) or {}
        expected_node = p.stem
        if expected_node not in node:
            errs.append(f"{p.name}: file name is not a node id")
        for i, it in enumerate(data.get("items", [])):
            where = f"{p.name}[{i}]"
            errs += [f"{where}: {m}" for m in schema_errors(it, "item.schema.json")]
            iid, nid = it.get("id"), it.get("node")
            if iid in seen:
                errs.append(f"{where}: duplicate item id {iid}")
            seen.add(iid)
            if nid not in node:
                errs.append(f"{where}: unknown node '{nid}'")
                continue
            if nid != expected_node:
                errs.append(f"{where}: node '{nid}' does not match file '{expected_node}'")
            if node[nid].get("kind") == "tag":
                errs.append(f"{where}: items cannot attach to tag node")
            if it.get("type") == "choice" and it.get("answer") not in it.get("choices", []):
                errs.append(f"{where}: answer not in choices")
            st = it.get("review", {}).get("status")
            if st == "approved" and not it["review"].get("by"):
                errs.append(f"{where}: approved without reviewer")
            stats[nid]["total"] += 1
            if st in ("approved", "pending"):
                stats[nid][st] += 1
    return errs, stats


def to_mermaid(g: dict) -> str:
    def sid(i):
        return i.replace(".", "_")
    lines = ["graph TD"]
    for n in g["nodes"]:
        mark = " *" if n.get("milestone") == "proto1" else ""
        shape = f'(("{n["label"]}"))' if n.get("kind") == "tag" else f'["{n["label"]}{mark}"]'
        lines.append(f"  {sid(n['id'])}{shape}")
    for e in g["edges"]:
        t = e.get("type", "prereq")
        arrow = "-->" if t == "prereq" else f"-.{e.get('note', t)}.->"
        lines.append(f"  {sid(e['from'])} {arrow} {sid(e['to'])}")
    lines.append("  classDef proto1 fill:#dbeafe,stroke:#1d4ed8")
    p1 = [sid(n["id"]) for n in g["nodes"] if n.get("milestone") == "proto1"]
    if p1:
        lines.append(f"  class {','.join(p1)} proto1")
    body = "\n".join(lines)
    return ("# Roadmap\n\nAuto-generated by `tools/validate.py --mermaid`. Do not edit.\n"
            "`*` = prototype 1 content node.\n\n```mermaid\n" + body + "\n```\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mermaid", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    g = load_yaml(GRAPH)
    errs = graph_errors(g)
    ierrs, stats = ([], {}) if errs else item_errors(g)
    errs += ierrs

    if not errs:
        md = to_mermaid(g)
        if a.mermaid:
            ROADMAP.parent.mkdir(exist_ok=True)
            ROADMAP.write_text(md, encoding="utf-8")
        if a.check and (not ROADMAP.exists() or ROADMAP.read_text(encoding="utf-8") != md):
            errs.append("docs/roadmap.md is stale: run tools/validate.py --mermaid")

    for e in errs:
        print(f"ERROR {e}")
    n_nodes, n_edges = len(g.get("nodes", [])), len(g.get("edges", []))
    print(f"graph: {n_nodes} nodes, {n_edges} edges")
    for nid, s in sorted(stats.items()):
        print(f"items {nid}: {s['total']} total, {s['approved']} approved, {s['pending']} pending review")
    print("FAIL" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
