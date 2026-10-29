"""Dependency-free SVG renderers for the chaining traces.

Each public function takes a ``graph`` dict produced by ``reasoning_engine``
and returns ``(svg, width, height)`` so the caller can size an HTML iframe.
Backward chains are drawn as a top-down proof tree; forward chains as a
left-to-right derivation DAG. No layout library is required.
"""

import html
from collections import defaultdict, deque

BOX_H = 40
PAD_X = 10
FONT = 12
CHAR_W = 6.6
H_GAP = 28
V_GAP = 78
ROW_H = 58

_FILL = {
    "proved": "#d7ecd9", "satisfied": "#d7ecd9",
    "initial": "#d6e4ff", "derived": "#d6e4ff",
    "applied": "#fff2cc", "failed": "#f8d7d2",
    "cycle": "#f8d7d2", "pending": "#eceff1",
}
_STROKE = {
    "proved": "#2e7d32", "satisfied": "#2e7d32",
    "initial": "#1565c0", "derived": "#1565c0",
    "applied": "#b26a00", "failed": "#c62828",
    "cycle": "#c62828", "pending": "#607d8b",
}


def _style(status):
    return _FILL.get(status, "#eceff1"), _STROKE.get(status, "#607d8b")


def _box_w(label):
    return max(54, int(len(label) * CHAR_W) + 2 * PAD_X)


def _escape(s):
    return html.escape(s, quote=True)


def _marker():
    return ('<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="8" refY="3.5" '
            'orient="auto" markerUnits="strokeWidth">'
            '<path d="M0,0 L10,3.5 L0,7 z" fill="#5f6368"/></marker></defs>')


def _box(x, y, w, label, status, target=False):
    fill, stroke = _style(status)
    sw = 3 if target else 1.4
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BOX_H}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + BOX_H / 2 + 4:.1f}" font-size="{FONT}" '
            f'fill="#202124" text-anchor="middle">{_escape(label)}</text>')


def _legend(items, y):
    x = 10
    parts = []
    for status, label in items:
        fill, stroke = _style(status)
        parts.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" '
                     f'fill="{fill}" stroke="{stroke}"/>')
        parts.append(f'<text x="{x + 16}" y="{y + 11}" font-size="11" '
                     f'fill="#202124">{_escape(label)}</text>')
        x += 16 + len(label) * 6.2 + 24
    return "\n".join(parts)


def _reachable(edges, focus):
    adj = defaultdict(list)
    for e in edges:
        adj[e["to"]].append(e["from"])
    seen = set()
    stack = list(focus)
    while stack:
        u = stack.pop()
        if u in seen:
            continue
        seen.add(u)
        stack.extend(adj[u])
    return seen


def render_backward_svg(graph):
    nodes = graph["nodes"]
    edges = graph["edges"]

    children = defaultdict(list)
    parent = {}
    for e in edges:
        children[e["from"]].append(e["to"])
        parent[e["to"]] = e["from"]

    roots = [n["id"] for n in nodes if n["id"] not in parent]

    depth = {}

    def assign_depth(u, d):
        depth[u] = d
        for c in children[u]:
            assign_depth(c, d + 1)

    for r in roots:
        assign_depth(r, 0)

    slot = [0]
    x_slot = {}

    def assign_x(u):
        ch = children[u]
        if not ch:
            x_slot[u] = slot[0]
            slot[0] += 1
            return
        for c in ch:
            assign_x(c)
        x_slot[u] = (x_slot[ch[0]] + x_slot[ch[-1]]) / 2.0

    for r in roots:
        assign_x(r)

    max_w = max(_box_w(n["label"]) for n in nodes) if nodes else 60
    pitch = max_w + H_GAP
    max_depth = max(depth.values()) if depth else 0

    width = max(1, slot[0]) * pitch
    height = (max_depth + 1) * V_GAP + BOX_H + 46

    def cx(u):
        return x_slot.get(u, 0) * pitch + pitch / 2.0

    def cy(u):
        return depth.get(u, 0) * V_GAP + 20

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" '
             f'height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}" '
             f'font-family="monospace">',
             _marker()]

    for e in edges:
        x1, y1 = cx(e["from"]), cy(e["from"]) + BOX_H
        x2, y2 = cx(e["to"]), cy(e["to"])
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="#5f6368" stroke-width="1.4" marker-end="url(#arrow)"/>')
        if e.get("label"):
            parts.append(f'<text x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2 - 4:.1f}" '
                         f'font-size="10" fill="#5f6368" text-anchor="middle">'
                         f'{_escape(e["label"])}</text>')

    for n in nodes:
        x = cx(n["id"]) - _box_w(n["label"]) / 2.0
        parts.append(_box(x, cy(n["id"]), _box_w(n["label"]), n["label"], n["status"]))

    parts.append(_legend([("proved", "proved / satisfied"),
                          ("failed", "failed / cycle"),
                          ("applied", "rule")], int(height) - 26))
    parts.append("</svg>")
    return "\n".join(parts), int(width), int(height)


def render_forward_svg(graph):
    nodes = graph["nodes"]
    edges = graph["edges"]
    by_id = {n["id"]: n for n in nodes}

    focus = graph.get("focus")
    if not focus:
        focus = [graph["target"]] if graph.get("target") is not None else [n["id"] for n in nodes]
    keep = _reachable(edges, focus) or {n["id"] for n in nodes}

    f_nodes = [n for n in nodes if n["id"] in keep]
    f_edges = [e for e in edges if e["from"] in keep and e["to"] in keep]

    indeg = defaultdict(int)
    children = defaultdict(list)
    for e in f_edges:
        indeg[e["to"]] += 1
        children[e["from"]].append(e["to"])

    layer = {n["id"]: 0 for n in f_nodes}
    q = deque(n["id"] for n in f_nodes if indeg[n["id"]] == 0)
    while q:
        u = q.popleft()
        for c in children[u]:
            layer[c] = max(layer[c], layer[u] + 1)
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)

    by_layer = defaultdict(list)
    for n in f_nodes:
        by_layer[layer[n["id"]]].append(n["id"])
    for k in by_layer:
        by_layer[k].sort()

    max_w = max(_box_w(n["label"]) for n in f_nodes) if f_nodes else 60
    col_w = max_w + H_GAP
    max_nodes = max(len(v) for v in by_layer.values()) if by_layer else 1
    max_layer = max(layer.values()) if layer else 0

    width = (max_layer + 1) * col_w + 10
    height = max_nodes * ROW_H + 46

    pos = {}
    for k, ids in by_layer.items():
        for i, nid in enumerate(ids):
            pos[nid] = (k * col_w + 10, i * ROW_H + 20)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" '
             f'height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}" '
             f'font-family="monospace">',
             _marker()]

    for e in f_edges:
        x1 = pos[e["from"]][0] + _box_w(by_id[e["from"]]["label"])
        y1 = pos[e["from"]][1] + BOX_H / 2
        x2 = pos[e["to"]][0]
        y2 = pos[e["to"]][1] + BOX_H / 2
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="#5f6368" stroke-width="1.4" marker-end="url(#arrow)"/>')

    target_id = graph.get("target")
    for n in f_nodes:
        x, y = pos[n["id"]]
        parts.append(_box(x, y, _box_w(n["label"]), n["label"], n["status"],
                          target=(n["id"] == target_id)))

    parts.append(_legend([("initial", "given fact"),
                          ("derived", "derived fact"),
                          ("derived", "bold = target")], int(height) - 26))
    parts.append("</svg>")
    return "\n".join(parts), int(width), int(height)
