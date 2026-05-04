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
    """Genera un file HTML autosufficiente con grafo interattivo D3.js.

    Args:
        memories: Lista di dict con almeno id, content, category, importance.
        edges: Lista di dict con source_id, target_id, relation, confidence_type.
        partition: {memory_id: community_id} per colorare i nodi.
        title: Titolo della pagina HTML.

    Returns:
        Stringa HTML completa (pronta per salvare come .html).
    """
    # Prepara dati per JSON embeddato
    nodes_data = []
    mem_map = {m["id"]: m for m in memories}

    for m in memories:
        mid = m["id"]
        # Prendi prime 60 parole per preview
        content_preview = m.get("content", "")[:200]
        community_id = (partition or {}).get(mid, -1)

        nodes_data.append({
            "id": mid,
            "label": f"#{mid}",
            "category": m.get("category", "note"),
            "importance": m.get("importance", 5),
            "community": community_id,
            "preview": content_preview,
            "tags": m.get("tags", ""),
            "created": str(m.get("created_at", ""))[:10],
        })

    edges_data = []
    for e in edges:
        # Solo edge tra nodi esistenti
        src = e.get("source_id") or e.get("source")
        tgt = e.get("target_id") or e.get("target")
        if src in mem_map and tgt in mem_map:
            edges_data.append({
                "source": src,
                "target": tgt,
                "relation": e.get("relation", "related"),
                "confidence": e.get("confidence_type", "extracted"),
                "weight": e.get("weight", 1.0),
            })

    # Colori per community (fino a 30 comunità)
    COMMUNITY_COLORS = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
        "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
        "#86bcf9", "#d4a6c8", "#a1c9e0", "#c5b0d5", "#ffbb78",
        "#98df8a", "#ff9896", "#c49c94", "#c7c7c7", "#dbdb8d",
        "#bcbd22", "#17becf", "#e377c2", "#8c564b", "#7f7f7f",
        "#9467bd", "#2ca02c", "#d62728", "#1f77b4", "#ff7f0e",
    ]

    CATEGORY_COLORS = {
        "decision": "#e15759",
        "discovery": "#59a14f",
        "bugfix": "#edc948",
        "feature": "#4e79a7",
        "refactor": "#76b7b2",
        "change": "#f28e2b",
        "note": "#b07aa1",
    }

    CONFIDENCE_COLORS = {
        "extracted": "#4CAF50",
        "inferred": "#FFC107",
        "ambiguous": "#F44336",
    }

    # Colore per nodi non clusterizzati
    UNASSIGNED_COLOR = "#cccccc"

    nodes_json = json.dumps(nodes_data)
    edges_json = json.dumps(edges_data)
    community_colors_json = json.dumps(COMMUNITY_COLORS)
    category_colors_json = json.dumps(CATEGORY_COLORS)
    confidence_colors_json = json.dumps(CONFIDENCE_COLORS)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_mod.escape(title)}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #1a1a2e; color: #e0e0e0; overflow: hidden; }}
#container {{ display: flex; height: 100vh; }}
#sidebar {{ width: 320px; background: #16213e; padding: 16px; overflow-y: auto; border-right: 1px solid #0f3460; }}
#sidebar h2 {{ font-size: 16px; margin: 0 0 12px 0; color: #e94560; }}
#sidebar label {{ display: block; font-size: 12px; margin-bottom: 4px; color: #aaa; }}
#sidebar select, #sidebar input {{ width: 100%; padding: 8px; margin-bottom: 12px;
       background: #0f3460; color: #e0e0e0; border: 1px solid #1a1a4e; border-radius: 4px; }}
#sidebar .stat {{ display: flex; justify-content: space-between; padding: 4px 0;
       font-size: 12px; border-bottom: 1px solid #1a1a4e; }}
#sidebar .stat span:first-child {{ color: #888; }}
#graph-container {{ flex: 1; position: relative; }}
#graph-container svg {{ width: 100%; height: 100%; }}
.node {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
.node:hover {{ stroke: #e94560; stroke-width: 2.5px; }}
.link {{ stroke-opacity: 0.6; }}
.link.extracted {{ stroke: #4CAF50; }}
.link.inferred {{ stroke: #FFC107; }}
.link.ambiguous {{ stroke: #F44336; }}
.label {{ font-size: 10px; fill: #ccc; pointer-events: none; }}
#tooltip {{ position: absolute; display: none; background: #16213e; border: 1px solid #e94560;
       border-radius: 6px; padding: 10px; font-size: 12px; max-width: 300px;
       box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 100; }}
#tooltip .tt-title {{ font-weight: bold; color: #e94560; margin-bottom: 4px; }}
#tooltip .tt-detail {{ color: #aaa; font-size: 11px; }}
#tooltip .tt-content {{ margin-top: 6px; color: #ccc; }}
#legend {{ position: absolute; bottom: 20px; left: 340px; background: #16213ee0;
       padding: 12px; border-radius: 6px; font-size: 11px; }}
#legend div {{ display: flex; align-items: center; gap: 6px; margin: 2px 0; }}
#legend .swatch {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
#search-box {{ position: absolute; top: 16px; left: 340px; z-index: 10; }}
#search-box input {{ width: 250px; padding: 8px 12px; background: #16213e; color: #e0e0e0;
       border: 1px solid #0f3460; border-radius: 20px; font-size: 13px; }}
</style>
</head>
<body>
<div id="container">
  <div id="sidebar">
    <h2>{html_mod.escape(title)}</h2>
    <label>Color by</label>
    <select id="color-mode">
      <option value="community">Community</option>
      <option value="category">Category</option>
    </select>
    <label>Confidence filter</label>
    <select id="confidence-filter">
      <option value="all">All</option>
      <option value="extracted">EXTRACTED</option>
      <option value="inferred">INFERRED</option>
      <option value="ambiguous">AMBIGUOUS</option>
    </select>
    <label>Category filter</label>
    <select id="category-filter">
      <option value="all">All</option>
      <option value="decision">decision</option>
      <option value="discovery">discovery</option>
      <option value="bugfix">bugfix</option>
      <option value="feature">feature</option>
      <option value="refactor">refactor</option>
      <option value="change">change</option>
      <option value="note">note</option>
    </select>
    <div id="stats"></div>
  </div>
  <div id="graph-container">
    <div id="search-box"><input id="search" type="text" placeholder="Search nodes..." /></div>
    <div id="legend">
      <div><span class="swatch" style="background:#4CAF50"></span> EXTRACTED</div>
      <div><span class="swatch" style="background:#FFC107"></span> INFERRED</div>
      <div><span class="swatch" style="background:#F44336"></span> AMBIGUOUS</div>
    </div>
  </div>
</div>
<div id="tooltip"></div>

<script>
const nodes = {nodes_json};
const edges = {edges_json};
const communityColors = {community_colors_json};
const categoryColors = {category_colors_json};
const confidenceColors = {confidence_colors_json};
const UNASSIGNED = "{UNASSIGNED_COLOR}";

const width = document.getElementById('graph-container').clientWidth;
const height = document.getElementById('graph-container').clientHeight;

const svg = d3.select('#graph-container').append('svg')
    .attr('width', width).attr('height', height);

const g = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', (e) => g.attr('transform', e.transform));
svg.call(zoom);

function getNodeColor(d, mode) {{
    if (mode === 'community') {{
        return d.community >= 0 ? communityColors[d.community % communityColors.length] : UNASSIGNED;
    }} else {{
        return categoryColors[d.category] || '#888';
    }}
}}

function updateGraph(colorMode) {{
    // Filter edges by confidence
    const confFilter = document.getElementById('confidence-filter').value;
    const catFilter = document.getElementById('category-filter').value;
    const searchTerm = document.getElementById('search')?.value?.toLowerCase() || '';

    const visibleEdges = edges.filter(e =>
        confFilter === 'all' || e.confidence === confFilter
    );
    const edgeNodeIds = new Set();
    visibleEdges.forEach(e => {{ edgeNodeIds.add(e.source); edgeNodeIds.add(e.target); }});

    const visibleNodes = nodes.filter(n =>
        edgeNodeIds.has(n.id) &&
        (catFilter === 'all' || n.category === catFilter) &&
        (!searchTerm || n.preview.toLowerCase().includes(searchTerm) || n.label.includes(searchTerm))
    );
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    const filteredEdges = visibleEdges.filter(e =>
        visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
    );

    // Stats
    const statsDiv = document.getElementById('stats');
    const communities = new Set(visibleNodes.map(n => n.community)).size;
    statsDiv.innerHTML = `
        <div class="stat"><span>Nodes</span><span>${{visibleNodes.length}}</span></div>
        <div class="stat"><span>Edges</span><span>${{filteredEdges.length}}</span></div>
        <div class="stat"><span>Communities</span><span>${{communities > 0 ? communities : '-'}}</span></div>
    `;

    // Simulation
    const simulation = d3.forceSimulation(visibleNodes)
        .force('link', d3.forceLink(filteredEdges).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-150))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => 5 + d.importance));

    // Links
    g.selectAll('.link').remove();
    const link = g.selectAll('.link')
        .data(filteredEdges).join('line')
        .attr('class', d => `link ${{d.confidence}}`)
        .attr('stroke-width', d => Math.max(0.5, d.weight * 2));

    // Nodes
    g.selectAll('.node-group').remove();
    const node = g.selectAll('.node-group')
        .data(visibleNodes).join('g')
        .attr('class', 'node-group')
        .call(d3.drag()
            .on('start', (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
            .on('drag', (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
            .on('end', (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }})
        );

    node.append('circle')
        .attr('class', 'node')
        .attr('r', d => 4 + d.importance * 1.5)
        .attr('fill', d => getNodeColor(d, colorMode));

    node.append('text')
        .attr('class', 'label')
        .attr('dx', d => 7 + d.importance * 1.5)
        .attr('dy', 4)
        .text(d => d.label);

    // Tooltip
    node.on('mouseover', (e, d) => {{
        const tip = d3.select('#tooltip');
        tip.style('display', 'block')
            .html(`
                <div class="tt-title">#${{d.id}} [${{d.category}}]</div>
                <div class="tt-detail">importance=${{d.importance}} community=${{d.community >= 0 ? d.community : '-'}} ${{d.created}}</div>
                <div class="tt-content">${{d.preview}}</div>
            `)
            .style('left', (e.offsetX + 10) + 'px')
            .style('top', (e.offsetY - 10) + 'px');
    }}).on('mouseout', () => d3.select('#tooltip').style('display', 'none'));

    // Tick
    simulation.on('tick', () => {{
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('transform', d => `translate($${{d.x}},$${{d.y}})`);
    }});
}}

// Initial render
updateGraph('community');

// Event listeners
document.getElementById('color-mode').onchange = (e) => updateGraph(e.target.value);
document.getElementById('confidence-filter').onchange = () => updateGraph(document.getElementById('color-mode').value);
document.getElementById('category-filter').onchange = () => updateGraph(document.getElementById('color-mode').value);
document.getElementById('search').oninput = () => updateGraph(document.getElementById('color-mode').value);

// Handle resize
window.addEventListener('resize', () => {{
    const w = document.getElementById('graph-container').clientWidth;
    const h = document.getElementById('graph-container').clientHeight;
    svg.attr('width', w).attr('height', h);
    updateGraph(document.getElementById('color-mode').value);
}});
</script>
</body>
</html>"""

    return html_template
