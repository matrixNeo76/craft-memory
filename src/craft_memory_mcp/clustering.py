"""
Community Detection per Craft Memory.

Usa l'algoritmo Louvain (via python-louvain) per raggruppare
i nodi del grafo in comunità semanticamente coerenti.

Dipendenze:
    - networkx (già installato)
    - python-louvain (pip install python-louvain)

Uso:
    from craft_memory_mcp.clustering import detect_communities

    communities = detect_communities(memories, edges)
    # {memory_id: community_id}
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_HAS_LOUVAIN = False
try:
    import community as _community_louvain  # python-louvain
    _HAS_LOUVAIN = True
except ImportError:
    pass

import networkx as nx


def detect_communities(
    memories: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    resolution: float = 1.0,
) -> dict[int, int]:
    """Applica community detection (Leiden/Louvain) al grafo.

    Args:
        memories: Lista di dict con almeno 'id' e 'importance'.
        edges: Lista di dict con 'source_id', 'target_id', e opzionale 'weight'.
        resolution: Parametro di risoluzione del clustering.
                    >1.0 = più comunità, <1.0 = meno comunità (default: 1.0).

    Returns:
        dict {memory_id: community_id} per ogni nodo nel grafo.
        I community_id sono interi (0, 1, 2, ...).
        Nodi isolati (senza edge) non vengono inclusi.
    """
    if not edges:
        logger.info("Nessun edge trovato — impossibile clusterizzare.")
        return {}

    G = nx.Graph()

    # Aggiungi nodi con weight = importance per dimensioni
    mem_map = {m["id"]: m for m in memories}
    for m in memories:
        G.add_node(m["id"], importance=m.get("importance", 5))

    # Aggiungi edge con peso
    for e in edges:
        weight = e.get("weight", 1.0)
        src = e.get("source_id") or e.get("source")
        tgt = e.get("target_id") or e.get("target")
        if src is not None and tgt is not None:
            G.add_edge(src, tgt, weight=weight)

    # Applica community detection
    if _HAS_LOUVAIN:
        partition = _community_louvain.best_partition(G, resolution=resolution)
        logger.info(f"Louvain: {len(set(partition.values()))} communities su {len(partition)} nodi.")
    else:
        # Fallback: connected components (se Louvain non disponibile)
        logger.warning("python-louvain non installato. Uso connected components come fallback.")
        comps = nx.community.greedy_modularity_communities(G, weight="weight")
        partition = {}
        for cid, nodes in enumerate(comps):
            for node in nodes:
                partition[node] = cid

    return dict(partition)


def get_community_stats(
    partition: dict[int, int],
) -> list[dict[str, Any]]:
    """Statistiche sulle comunità rilevate.

    Args:
        partition: {memory_id: community_id}

    Returns:
        Lista di dict con community_id, size, e member_ids.
    """
    from collections import Counter

    counter = Counter(partition.values())
    stats = []
    for cid, count in counter.most_common():
        members = [mid for mid, c in partition.items() if c == cid]
        stats.append({
            "community_id": cid,
            "size": count,
            "member_ids": members,
        })
    return stats
