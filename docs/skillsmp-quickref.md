# SkillsMP Quick Reference (v2)

## MCP Source
- **Source slug:** `skillsmp`
- **Server:** `craft-memory/skills/skillsmp-mcp/server.py` (v2, 5 tools)
- **Skill:** `.agents/skills/skillsmp-checker/SKILL.md`
- **Struttura skill:** `craft-memory/data/skill_structure.json` (608 skill, 17 domini)
- **XLSX Inventory:** `craft-memory/docs/skill_inventory.xlsx`
- **Scripts:** `craft-memory/scripts/`

## 5 Tools Disponibili

| Tool | Cosa fa | Parametri |
|------|---------|-----------|
| `skillsmp_search` | Keyword search | q, category, sort_by, limit, format |
| `skillsmp_ai_search` | AI semantic search | q, format |
| `skillsmp_check_skill` | Verifica skill locale | skill_name, author_hint, format |
| `skillsmp_compare_skills` | Confronto con alternative | skill_name, local_stars, format |
| `skillsmp_scan_domain` | Scansiona intero dominio | domain_query, format |

Tutti i tool supportano `format="json"` per output machine-readable.

## Scripts Utili

```bash
# Genera XLSX base
cd craft-memory/scripts && python3 generate_xlsx.py

# Genera XLSX con dati SkillsMP (stelle, date, autore)
cd craft-memory/scripts && SKILLSMP_API_KEY="..." python3 generate_xlsx.py --with-skillsmp

# Mostra tutte le skill verificate su SkillsMP
cd craft-memory/scripts && SKILLSMP_API_KEY="..." python3 show_all_skills.py
```

## Miglioramenti v2
- Retry con exponential backoff (3 tentativi)
- Rate limit tracking (500/giorno)
- Cache adattiva (skill stabili = cache 10min)
- Output JSON opzionale su tutti i tool
- skillsmp_scan_domain per scansione domini interi
- Struttura skill centralizzata in JSON
- XLSX con colonne stelle/date/autore + statistiche

## Limiti
- API: 500 req/giorno, 30/min
- Cache: TTL 300s (default), 600s (skill >1000 stelle)
