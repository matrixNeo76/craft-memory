"""
SkillsMP MCP Server v2 — Cerca e confronta skill da skillsmp.com
===============================================================

Tools:
  - skillsmp_search: keyword search
  - skillsmp_ai_search: AI semantic search
  - skillsmp_check_skill: trova una skill locale su SkillsMP
  - skillsmp_compare_skills: confronta skill locale con alternative
  - skillsmp_scan_domain: scansiona un intero dominio di skill locali

v2 miglioramenti:
  - Retry con exponential backoff (3 tentativi)
  - Rate limit tracking giornaliero
  - Cache adattiva (pattern stabili = cache piu lunga)
  - Output JSON opzionale (formato json)
  - Tool skillsmp_scan_domain per domini interi
"""

import os
import time
import json
import httpx
import datetime
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────
API_BASE = "https://skillsmp.com/api/v1"
API_KEY = os.environ.get("SKILLSMP_API_KEY", "")
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
SKILLS_DIR = os.path.expanduser("~/.agents/skills")

# ══════════════════════════════════════════════════════════════════════
#  Rate Limit Tracker
# ══════════════════════════════════════════════════════════════════════

class RateLimitTracker:
    """Traccia le chiamate API SkillsMP giornaliere."""
    def __init__(self, daily_limit=500):
        self.daily_limit = daily_limit
        self.calls_today = 0
        self.last_reset = time.time()
        self.last_remaining = None
        self.last_reset_ts = None

    def _check_reset(self):
        now = time.time()
        day_seconds = 86400
        if now - self.last_reset > day_seconds:
            self.calls_today = 0
            self.last_reset = now

    def record_call(self, response=None):
        self._check_reset()
        self.calls_today += 1
        if response and "X-RateLimit-Daily-Remaining" in response.headers:
            self.last_remaining = int(response.headers["X-RateLimit-Daily-Remaining"])
        if response and "X-RateLimit-Daily-Reset" in response.headers:
            self.last_reset_ts = response.headers["X-RateLimit-Daily-Reset"]

    def is_near_limit(self, threshold=50):
        self._check_reset()
        remaining = self.daily_limit - self.calls_today
        return remaining <= threshold

    def remaining(self):
        self._check_reset()
        if self.last_remaining is not None:
            return min(self.last_remaining, self.daily_limit - self.calls_today)
        return self.daily_limit - self.calls_today

    def summary(self):
        self._check_reset()
        return f"API calls today: {self.calls_today}/{self.daily_limit}, remaining: {self.remaining()}"

_tracker = RateLimitTracker()

# ══════════════════════════════════════════════════════════════════════
#  Cache adattiva (TTL variabile)
# ══════════════════════════════════════════════════════════════════════

_cache: dict[str, tuple[float, dict]] = {}
DEFAULT_TTL = 300
STABLE_TTL = 600  # per skill con >1000 stelle

def _get_ttl(data: dict) -> int:
    """TTL piu lungo per skill stabili (tante stelle)."""
    skills = data.get("data", {}).get("skills", [])
    if skills:
        max_stars = max(s.get("stars", 0) for s in skills)
        if max_stars >= 1000:
            return STABLE_TTL
    return DEFAULT_TTL

# ══════════════════════════════════════════════════════════════════════
#  HTTP call con retry + rate limit tracking
# ══════════════════════════════════════════════════════════════════════

def _api_call(url: str, params: dict) -> dict:
    """Chiamata API SkillsMP con retry, backoff e rate limit tracking."""
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            _tracker.record_call(resp)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit colpito — aspetta e riprova
                wait = (2 ** attempt) * 5
                time.sleep(wait)
                last_error = e
                continue
            raise
        except httpx.RequestError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    raise last_error or httpx.RequestError("Max retries exceeded")


def _cached_or_fetch(cache_key: str, url: str, params: dict) -> dict:
    """Helper con cache adattiva."""
    now = time.time()
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < _get_ttl(data):
            return data

    try:
        data = _api_call(url, params)
        _cache[cache_key] = (time.time(), data)
        return data
    except httpx.HTTPStatusError as e:
        # Usa cache scaduta se disponibile come fallback
        if cache_key in _cache:
            ts, data = _cache[cache_key]
            return data
        raise
    except httpx.RequestError as e:
        if cache_key in _cache:
            ts, data = _cache[cache_key]
            return data
        raise


def _format_date(updated: str) -> str:
    if not updated:
        return "-"
    try:
        return datetime.datetime.fromtimestamp(int(updated)).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return str(updated)


def _format_search_results(q: str, data: dict, limit: int = 10) -> str:
    """Formatta risultati ricerca in testo markdown."""
    skills = data.get("data", {}).get("skills", [])
    if not skills:
        return f"Nessuna skill trovata per '{q}'."

    pag = data.get("data", {}).get("pagination", {})
    total = pag.get("total", "?")
    rate_note = f"\n\n📊 {_tracker.summary()}" if _tracker.remaining() < 200 else ""

    lines = [
        f"## 🔍 Risultati per '{q}'  ({total} totali, mostrati {len(skills)}){rate_note}",
        "",
    ]
    for s in skills:
        stars = s.get("stars", 0)
        updated = _format_date(s.get("updatedAt", ""))
        lines.append(f"### ⭐ {stars} | {s['name']} — by {s.get('author', '?')}")
        lines.append(f"   _{s.get('description', '')}_")
        lines.append(f"   📅 Aggiornato: {updated}")
        lines.append(f"   🔗 {s.get('skillUrl', '')}")
        lines.append("")

    return "\n".join(lines)


def _format_search_results_json(data: dict) -> str:
    """Formatta risultati ricerca in JSON."""
    skills = data.get("data", {}).get("skills", [])
    pag = data.get("data", {}).get("pagination", {})
    result = {
        "total": pag.get("total", len(skills)),
        "returned": len(skills),
        "skills": [
            {
                "name": s.get("name"),
                "author": s.get("author"),
                "stars": s.get("stars", 0),
                "updated": _format_date(s.get("updatedAt", "")),
                "description": s.get("description", ""),
                "url": s.get("skillUrl", ""),
            }
            for s in skills
        ],
        "rate_limit": {
            "remaining": _tracker.remaining(),
            "daily_limit": _tracker.daily_limit,
            "calls_today": _tracker.calls_today,
        }
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════
#  Struttura skill locali (da JSON o default)
# ══════════════════════════════════════════════════════════════════════

SKILL_STRUCTURE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "skill_structure.json"
)

def _load_skill_structure() -> dict:
    """Carica struttura skill da file JSON o restituisce struttura vuota."""
    if os.path.exists(SKILL_STRUCTURE_PATH):
        try:
            with open(SKILL_STRUCTURE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"domains": []}


# ══════════════════════════════════════════════════════════════════════
#  MCP Server
# ══════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "SkillsMP",
    instructions="Cerca e confronta skill AI da skillsmp.com",
)


@mcp.tool(
    description=(
        "Cerca skill su SkillsMP per parola chiave. "
        "Supporta filtri per categoria, ordinamento (stars/recent) e limite risultati. "
        "Opzione format='json' per output machine-readable."
    )
)
def skillsmp_search(
    q: str,
    category: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: int = 10,
    format: str = "text",
) -> str:
    """Keyword search su SkillsMP.

    Args:
        q: Query di ricerca (es. 'stripe payment', 'react components')
        category: Filtro categoria (es. 'payment', 'frontend', 'llm-ai', 'cicd')
        sort_by: Ordinamento — 'stars' (popolarita) o 'recent' (default)
        limit: Numero risultati (1-100, default 10)
        format: 'text' per output leggibile, 'json' per output strutturato
    """
    params = {"q": q, "limit": min(max(limit, 1), 100)}
    if category:
        params["category"] = category
    if sort_by:
        params["sortBy"] = sort_by

    try:
        data = _cached_or_fetch(f"search:{q}:{category}:{sort_by}", f"{API_BASE}/skills/search", params)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "message": str(e)})
    except httpx.RequestError as e:
        return json.dumps({"error": "connection_error", "message": str(e)})

    if not data.get("success"):
        return json.dumps({"error": "api_error", "message": str(data)})

    if format == "json":
        return _format_search_results_json(data)

    return _format_search_results(q, data, limit)


@mcp.tool(
    description=(
        "Ricerca semantica AI su SkillsMP. "
        "Usa Cloudflare AI per trovare skill pertinenti al significato. "
        "Opzione format='json' per output machine-readable."
    )
)
def skillsmp_ai_search(q: str, format: str = "text") -> str:
    """AI semantic search su SkillsMP.

    Args:
        q: Descrizione in linguaggio naturale (es. 'How to create a web scraper')
        format: 'text' o 'json'
    """
    try:
        data = _cached_or_fetch(f"ai:{q}", f"{API_BASE}/skills/ai-search", {"q": q})
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}"})
    except httpx.RequestError as e:
        return json.dumps({"error": "connection_error", "message": str(e)})

    if not data.get("success"):
        return json.dumps({"error": "api_error", "message": str(data)})

    results = data.get("data", {}).get("data", [])
    if not results:
        return json.dumps({"skills": []}) if format == "json" else f"Nessun risultato per '{q}'."

    if format == "json":
        out = {
            "query": q,
            "results": [
                {
                    "name": r.get("skill", {}).get("name"),
                    "author": r.get("skill", {}).get("author"),
                    "stars": r.get("skill", {}).get("stars", 0),
                    "score": round(r.get("score", 0), 4),
                    "updated": _format_date(r.get("skill", {}).get("updatedAt", "")),
                    "description": r.get("skill", {}).get("description", ""),
                    "url": r.get("skill", {}).get("skillUrl", ""),
                }
                for r in results
            ],
            "rate_limit": {
                "remaining": _tracker.remaining(),
                "calls_today": _tracker.calls_today,
            }
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    lines = [f"## 🧠 Risultati AI Search per '{q}'", ""]
    for r in results:
        s = r.get("skill", {})
        score = r.get("score", 0)
        stars = s.get("stars", 0)
        updated = _format_date(s.get("updatedAt", ""))
        lines.append(f"### 🎯 {float(score):.0%} match | ⭐ {stars} | {s['name']} — by {s.get('author', '?')}")
        lines.append(f"   _{s.get('description', '')}_")
        lines.append(f"   📅 Aggiornato: {updated}")
        lines.append(f"   🔗 {s.get('skillUrl', '')}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool(
    description=(
        "Cerca una skill specifica su SkillsMP e ne restituisce le statistiche. "
        "Utile per verificare se la versione locale e aggiornata. "
        "Opzione format='json' per output machine-readable."
    )
)
def skillsmp_check_skill(
    skill_name: str,
    author_hint: Optional[str] = None,
    format: str = "text",
) -> str:
    """Cerca una skill locale su SkillsMP e la confronta.

    Args:
        skill_name: Nome della skill (es. 'stripe-integration', 'supabase')
        author_hint: Suggerimento autore per filtrare (es. 'stripe', 'vercel')
        format: 'text' o 'json'
    """
    params = {"q": skill_name.replace("-", " "), "limit": 10, "sortBy": "stars"}
    try:
        data = _cached_or_fetch(f"check:{skill_name}", f"{API_BASE}/skills/search", params)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return json.dumps({"error": str(e)})

    skills = data.get("data", {}).get("skills", [])
    if not skills:
        return json.dumps({"found": False, "skill_name": skill_name}) if format == "json" else \
               f"Nessuna skill trovata per '{skill_name}' su SkillsMP."

    if author_hint:
        hint_lower = author_hint.lower()
        filtered = [s for s in skills if hint_lower in s.get("author", "").lower() or hint_lower in s.get("name", "").lower()]
        if filtered:
            skills = filtered

    if format == "json":
        out = {
            "skill_name": skill_name,
            "found": True,
            "results": [
                {
                    "name": s.get("name"),
                    "author": s.get("author"),
                    "stars": s.get("stars", 0),
                    "updated": _format_date(s.get("updatedAt", "")),
                    "description": s.get("description", ""),
                    "url": s.get("skillUrl", ""),
                }
                for s in skills[:5]
            ],
            "rate_limit": {
                "remaining": _tracker.remaining(),
                "calls_today": _tracker.calls_today,
            }
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    lines = [f"## 🔎 Risultati per '{skill_name}' su SkillsMP", ""]
    for s in skills[:5]:
        stars = s.get("stars", 0)
        updated = _format_date(s.get("updatedAt", ""))
        lines.append(f"### ⭐ {stars} | {s['name']} — by {s.get('author', '?')}")
        lines.append(f"   _{s.get('description', '')}_")
        lines.append(f"   📅 Aggiornato: {updated}  |  🔗 {s.get('skillUrl', '')}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool(
    description=(
        "Confronta una skill locale con le alternative su SkillsMP, "
        "ordinate per popolarita. Opzione format='json' per output machine-readable."
    )
)
def skillsmp_compare_skills(
    skill_name: str,
    local_stars: int = 0,
    format: str = "text",
) -> str:
    """Confronta skill locale con alternative su SkillsMP.

    Args:
        skill_name: Nome della skill locale
        local_stars: Stelle GitHub della skill locale (default 0)
        format: 'text' o 'json'
    """
    params = {"q": skill_name.replace("-", " "), "limit": 8, "sortBy": "stars"}
    try:
        data = _cached_or_fetch(f"compare:{skill_name}", f"{API_BASE}/skills/search", params)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return json.dumps({"error": str(e)})

    skills = data.get("data", {}).get("skills", [])
    if not skills:
        return json.dumps({"found": False, "skill_name": skill_name}) if format == "json" else \
               f"Nessuna alternativa trovata per '{skill_name}'."

    if format == "json":
        out = {
            "skill_name": skill_name,
            "local_stars": local_stars,
            "alternatives": [
                {
                    "name": s.get("name"),
                    "author": s.get("author"),
                    "stars": s.get("stars", 0),
                    "updated": _format_date(s.get("updatedAt", "")),
                    "is_better": s.get("stars", 0) > local_stars,
                    "description": s.get("description", ""),
                    "url": s.get("skillUrl", ""),
                }
                for s in skills[:6]
            ],
            "rate_limit": {
                "remaining": _tracker.remaining(),
                "calls_today": _tracker.calls_today,
            }
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    lines = [
        f"## 📊 Confronto: '{skill_name}'",
        f"**Skill locale:** ⭐ {local_stars}",
        f"**Skill trovate su SkillsMP:** {len(skills)}",
        "",
    ]
    for i, s in enumerate(skills[:6], 1):
        stars = s.get("stars", 0)
        updated = _format_date(s.get("updatedAt", ""))
        label = "MIGLIORE" if stars > local_stars else "SIMILE" if stars == local_stars else "MENO POPOLARE"
        lines.append(f"**{i}. {'⭐' if stars > local_stars else '↔'} {label}** {s['name']} by {s.get('author', '?')} (⭐ {stars})")
        lines.append(f"   _{s.get('description', '')}_")
        lines.append(f"   📅 {updated}")

    return "\n".join(lines)


@mcp.tool(
    description=(
        "Scansiona un intero dominio di skill locali su SkillsMP. "
        "Il dominio corrisponde a uno dei 17 del catalogo (es. '3. AI & AGENTS', '7. SECURITY'). "
        "Restituisce per ogni skill: stelle, data aggiornamento, autore. "
        "Opzione format='json' per output machine-readable."
    )
)
def skillsmp_scan_domain(
    domain_query: str,
    format: str = "text",
) -> str:
    """Scansiona tutte le skill di un dominio su SkillsMP.

    Args:
        domain_query: Nome o numero del dominio (es. '3', 'AI & AGENTS', '7. SECURITY')
        format: 'text' o 'json'
    """
    structure = _load_skill_structure()
    if not structure.get("domains"):
        return json.dumps({"error": "skill structure not found", "hint": "run generate_xlsx.py first"})

    # Trova il dominio per match parziale
    q = domain_query.lower().strip().rstrip(".")
    domain = None
    for d in structure["domains"]:
        key = f"{d.get('number', '')}. {d.get('name', '')}".lower()
        if q in key or q in d.get("name", "").lower() or q in str(d.get("number", "")):
            domain = d
            break

    if not domain:
        return json.dumps({"error": f"dominio '{domain_query}' non trovato",
                           "available": [f"{d.get('number')}. {d.get('name')}" for d in structure["domains"]]})

    # Raccogli tutte le skill del dominio
    all_skills = []
    for sub in domain.get("subdomains", []):
        for sk in sub.get("skills", []):
            if isinstance(sk, str):
                all_skills.append({"name": sk, "subdomain": sub.get("name", "")})
            else:
                all_skills.append({"name": sk["name"], "subdomain": sub.get("name", "")})

    if format == "json":
        results = []
        for sk in all_skills:
            try:
                data = _cached_or_fetch(f"check:{sk['name']}", f"{API_BASE}/skills/search",
                                         {"q": sk["name"].replace("-", " "), "limit": 3, "sortBy": "stars"})
                skills = data.get("data", {}).get("skills", [])
                if skills:
                    s = skills[0]
                    results.append({
                        "name": sk["name"],
                        "subdomain": sk["subdomain"],
                        "stars": s.get("stars", 0),
                        "author": s.get("author", ""),
                        "updated": _format_date(s.get("updatedAt", "")),
                        "url": s.get("skillUrl", ""),
                    })
                else:
                    results.append({"name": sk["name"], "subdomain": sk["subdomain"],
                                    "stars": 0})
            except:
                results.append({"name": sk["name"], "subdomain": sk["subdomain"], "error": "failed"})

        out = {
            "domain": f"{domain.get('number')}. {domain.get('name')}",
            "skills_checked": len(results),
            "skills": results,
            "rate_limit": {
                "remaining": _tracker.remaining(),
                "calls_today": _tracker.calls_today,
            }
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    # Formato testo
    lines = [f"## 📋 Scansione Dominio: {domain.get('number')}. {domain.get('name')}",
             f"Skill da verificare: {len(all_skills)}",
             f"📊 {_tracker.summary()}", ""]

    for sk in all_skills:
        try:
            data = _cached_or_fetch(f"check:{sk['name']}", f"{API_BASE}/skills/search",
                                     {"q": sk["name"].replace("-", " "), "limit": 3, "sortBy": "stars"})
            skills = data.get("data", {}).get("skills", [])
            if skills:
                s = skills[0]
                stars = s.get("stars", 0)
                updated = _format_date(s.get("updatedAt", ""))
                author = s.get("author", "")
                lines.append(f"  {sk['name']:40s}  ⭐ {int(stars):>6,}  📅 {updated}  👤 {author[:25]:25s}")
            else:
                lines.append(f"  {sk['name']:40s}  [non trovata su SkillsMP]")
        except:
            lines.append(f"  {sk['name']:40s}  [errore]")

    lines.append("")
    lines.append(f"✅ Verificate {len(all_skills)} skill — {_tracker.summary()}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  Avvio
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run(transport="stdio")
