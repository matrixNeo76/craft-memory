"""
Generazione grafo HTML interattivo per Craft Memory.

Usa D3.js force-directed graph con:
- Nodi colorati per community (Leiden/Louvain)
- Dimensione nodi per importance
- Tooltip con preview contenuto
- Barra di ricerca
- Legenda EXTRACTED/INFERRED/AMBIGUOUS
- Filtro per confidence type e tag

Dipendenze: nessuna (D3.js caricato via CDN).
"""

import json
import html as html_mod
from typing import Any


def generate_graph_html(
    memories: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    partition: dict[int, int] | None = None,
    title: str = "Craft Memory Graph",
) -> str:
    """Genera un file HTML autosufficiente con grafo interattivo D3.js."""
    from string import Template
    import os

    # Load template from file
    template_path = os.path.join(os.path.dirname(__file__), "templates", "graph.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_text = f.read()

    nodes_data = []
    mem_map = {m["id"]: m for m in memories}
    for m in memories:
        mid = m["id"]
        content_preview = m.get("content", "")[:200]
        community_id = (partition or {}).get(mid, -1)
        nodes_data.append({
            "id": mid, "label": f"#{mid}",
            "category": m.get("category", "note"),
            "importance": m.get("importance", 5),
            "community": community_id,
            "preview": content_preview,
            "tags": m.get("tags", ""),
            "created": str(m.get("created_at", ""))[:10],
        })

    edges_data = []
    for e in edges:
        src = e.get("source_id") or e.get("source")
        tgt = e.get("target_id") or e.get("target")
        if src in mem_map and tgt in mem_map:
            edges_data.append({
                "source": src, "target": tgt,
                "relation": e.get("relation", "related"),
                "confidence": e.get("confidence_type", "extracted"),
                "weight": e.get("weight", 1.0),
            })

    COMMUNITY_COLORS = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
        "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
        "#86bcf9", "#d4a6c8", "#a1c9e0", "#c5b0d5", "#ffbb78",
        "#98df8a", "#ff9896", "#c49c94", "#c7c7c7", "#dbdb8d",
        "#bcbd22", "#17becf", "#e377c2", "#8c564b", "#7f7f7f",
        "#9467bd", "#2ca02c", "#d62728", "#1f77b4", "#ff7f0e",
    ]
    CATEGORY_COLORS = {
        "decision": "#e15759", "discovery": "#59a14f", "bugfix": "#edc948",
        "feature": "#4e79a7", "refactor": "#76b7b2", "change": "#f28e2b", "note": "#b07aa1",
    }
    CONFIDENCE_COLORS = {"extracted": "#4CAF50", "inferred": "#FFC107", "ambiguous": "#F44336"}
    UNASSIGNED_COLOR = "#cccccc"

    template = Template(template_text)
    html = template.safe_substitute(
        title=html_mod.escape(title),
        nodes_json=json.dumps(nodes_data),
        edges_json=json.dumps(edges_data),
        community_colors_json=json.dumps(COMMUNITY_COLORS),
        category_colors_json=json.dumps(CATEGORY_COLORS),
        confidence_colors_json=json.dumps(CONFIDENCE_COLORS),
        UNASSIGNED_COLOR=json.dumps(UNASSIGNED_COLOR),
    )
    return html
