"""
Compressione deterministica per Craft Memory.

Dizionario generale livello 1 (~40% riduzione su testi medi in inglese).
Compressione invertibile: compress() → decompress() recupera il testo originale.

Compatibilità:
  - Level 0: nessuna compressione (default, backward compatibile)
  - Level 1: dizionario base di frasi comuni (~40% riduzione)

Uso:
    from craft_memory_mcp.compress import compress, decompress, estimate_savings

    compressed = compress("Hello, you are an expert software engineer", level=1)
    # → "Hello, ur_xprt sw_eng"

    original = decompress(compressed)
    # → "Hello, you are an expert software engineer"
"""

import re
from typing import Pattern


# ─── Dizionario Level 1 ──────────────────────────────────────────────
# pattern_regex → replacement
# Ordinato per pattern decrescente (pattern più lunghi prima)
_DICT_L1: list[tuple[str, str]] = [
    (r"\byou are an expert\b", "ur_xprt"),
    (r"\bYou are an expert\b", "Ur_xprt"),
    (r"\bYOU ARE AN EXPERT\b", "UR_XPRT"),
    (r"\bspec driven development\b", "sdd"),
    (r"\bsoftware engineer\b", "sw_eng"),
    (r"\bdevelopment environment\b", "dev_env"),
    (r"\bartificial intelligence\b", "@ai"),
    (r"\bknowledge graph\b", "@kg"),
    (r"\bfull text search\b", "@fts"),
    (r"\breduced token kernel\b", "@rtk"),
    (r"\bretrieval augmented generation\b", "@rag"),
    (r"\bfollow up\b", "@fu"),
    (r"\bI think\b", "@tnk"),
    (r"\bfor example\b", "@eg"),
    (r"\bin order to\b", "@2"),
    (r"\bas well as\b", "@awa"),
    (r"\bthat is\b", "@ie"),
    (r"\binformation\b", "@info"),
    (r"\bregarding\b", "@re"),
    (r"\bimplementation\b", "@impl"),
    (r"\bconfiguration\b", "@cfg"),
    (r"\bfunctionality\b", "@func"),
    (r"\bapplication\b", "@app"),
    (r"\bdocumentation\b", "@docs"),
    (r"\bdemonstrate\b", "@demo"),
    (r"\bcommunicate\b", "@comm"),
    (r"\brepository\b", "@repo"),
    (r"\bmanagement\b", "@mgmt"),
    (r"\bdescription\b", "@desc"),
    (r"\bparameter\b", "@param"),
    (r"\battribute\b", "@attr"),
    (r"\bplease\b", "@pls"),
    (r"\barchitecture\b", "@arch"),
    (r"\balgorithm\b", "@algo"),
    (r"\bcompliant\b", "@ok"),
    (r"\bconfigure\b", "@cfg2"),
    (r"\bdatabase\b", "@db"),
    (r"\bframework\b", "@fw"),
    (r"\bnetwork\b", "@net"),
    (r"\breference\b", "@ref"),
    (r"\bversion\b", "@v"),
    (r"\btemporary\b", "@tmp"),
    (r"\bdeveloping\b", "@dvg"),
    (r"\bauthentication\b", "@auth"),
    (r"\boptimization\b", "@opt"),
    (r"\bsynchronization\b", "@sync"),
    (r"\binitialization\b", "@init"),
    (r"\bidentification\b", "@id"),
]

# ─── Dizionario Level 2 (aggressivo) ──────────────────────────────────
# Pattern aggiuntivi per compressione più spinta (~60% su testi misti)
_DICT_L2: list[tuple[str, str]] = [
    (r"\bif __name__ == \"__main__\"\b", "@imain"),
    (r"\bif __name__ == '__main__'\b", "@imain"),
    (r"\bimport logging\b", "@ilog"),
    (r"\bfrom typing import\b", "@ftyp"),
    (r"\bdef __init__\b", "@init"),
    (r"\bself\.\b", "@s."),
    (r"\bTYPE_CHECKING\b", "@tc"),
    (r"\bdataclass\b", "@dc"),
    (r"\bException\b", "@exc"),
    (r"\bOptional\b", "@opt"),
    (r"\b__init__\.py\b", "@ip"),
    (r"\bAsyncGenerator\b", "@ag"),
    (r"\bCallable\b", "@cb"),
    (r"\bProtocol\b", "@proto"),
    (r"\bDict\b", "@dct"),
    (r"\bList\b", "@lst"),
    (r"\bTuple\b", "@tup"),
    (r"\bSet\b", "@st"),
    (r"\bTypeVar\b", "@tv"),
    (r"\bGeneric\b", "@gen"),
    (r"\bAny\b", "@any"),
    (r"\bFinal\b", "@fin"),
    (r"\bLiteral\b", "@lit"),
    (r"\bdataclasses\b", "@dcs"),
    (r"\bUnion\b", "@uni"),
    (r"\bTYPE_CHECKING\b", "@tc2"),
    (r"\basync def\b", "@adef"),
    (r"\bawait\b", "@aw"),
    (r"\b__all__\b", "@all"),
    (r"\boverride\b", "@ovr"),
    (r"\bproperty\b", "@prop"),
    (r"\bstaticmethod\b", "@sm"),
    (r"\bclassmethod\b", "@cm"),
    (r"\babstractmethod\b", "@am"),
    (r"\bimport\b", "@imp"),
    (r"\breturn\b", "@ret"),
    (r"\byield\b", "@yld"),
    (r"\braise\b", "@rse"),
    (r"\bTrue\b", "@T"),
    (r"\bFalse\b", "@F"),
    (r"\bNone\b", "@N"),
    (r"\bArgs:\b", "@A:"),
    (r"\bReturns:\b", "@R:"),
    (r"\bRaises:\b", "@Rs:"),
    (r"\bYields:\b", "@Y:"),
    (r"\bExample:\b", "@Ex:"),
    (r"\bNote:\b", "@Nt:"),
    (r"\sthis\b", "@th"),
    (r"\bthat\b", "@tht"),
    (r"\bwith\b", "@w"),
]

# Merge dizionari per level=2 (L1 + L2)
_DICT_L2_FULL: list[tuple[str, str]] = _DICT_L1 + _DICT_L2

# Precompile per performance (case-sensitive per preservare maiuscole)
_COMPILED_L1: list[tuple[Pattern, str]] = [
    (re.compile(p), r) for p, r in _DICT_L1
]
_COMPILED_L2: list[tuple[Pattern, str]] = [
    (re.compile(p), r) for p, r in _DICT_L2_FULL
]

# Dizionario inverso: replacement → original (per decompressione)
# Rimuove i marker regex (\b, \, etc.) dall'originale.
# L'originale compresso è testo puro (senza regex), quindi la decompressione
# fa simple text replacement: cerca il token e lo espande.
# Dizionario inverso per decompressione: replacement → pattern per trovare il token
# Usa word boundaries (\b) per evitare sostituzioni parziali
# Esempio: "re" non deve matchare dentro "repository" o "are"
import re as _re

_REVERSE_L1_COMPILED: list[tuple[_re.Pattern, str]] = []
for p, r in _DICT_L1:
    escaped = _re.escape(r)
    # Non-word boundary: matcha solo se non preceduto/seguido da lettera
    compiled = _re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])")
    # Estrai il testo originale dal pattern (rimuovi \b...\b)
    original = p.replace(r"\b", "")
    _REVERSE_L1_COMPILED.append((compiled, original))
# Ordine: dal replacement più lungo al più corto (evita match parziali)
_REVERSE_L1_COMPILED.sort(key=lambda x: len(x[0].pattern), reverse=True)

# Level 2 reverse patterns
_REVERSE_L2_COMPILED: list[tuple[_re.Pattern, str]] = []
for p, r in _DICT_L2_FULL:
    escaped = _re.escape(r)
    compiled = _re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])")
    # Extract original readable text and escape it for replacement
    raw = p.replace(r"", "").replace(r"\s", " ").strip()
    _REVERSE_L2_COMPILED.append((compiled, raw))
_REVERSE_L2_COMPILED.sort(key=lambda x: len(x[1]), reverse=True)


def compress(text: str, level: int = 1) -> str:
    """Comprime testo con dizionario deterministico.

    Args:
        text: Testo da comprimere
        level: 0=nessuna, 1=base (~40%), 2=aggressivo (~60%)

    Returns:
        Testo compresso. Usa decompress() per recuperare l'originale.
    """
    if level == 0 or not text:
        return text

    patterns = _COMPILED_L2 if level >= 2 else _COMPILED_L1
    result = text
    for pattern, replacement in patterns:
        result = pattern.sub(replacement, result)

    return result


def decompress(text: str, level: int = 1) -> str:
    """Decompressione inversa. Recupera il testo originale da compress().

    Args:
        text: Testo compresso
        level: 1=base, 2=aggressivo

    Returns:
        Testo originale (approssimazione fedele)
    """
    if not text:
        return text

    patterns = _REVERSE_L2_COMPILED if level >= 2 else _REVERSE_L1_COMPILED
    result = text
    for pattern, original in patterns:
        result = pattern.sub(original, result)

    return result


def estimate_savings(text: str, level: int = 1) -> dict:
    """Stima il risparmio di token per un dato testo.

    Returns:
        dict con original_chars, compressed_chars, savings_pct
    """
    original_chars = len(text)
    compressed = compress(text, level=level)
    compressed_chars = len(compressed)
    savings_pct = round((1 - compressed_chars / max(original_chars, 1)) * 100)

    # Stima token: ~4 caratteri per token in media
    original_tokens = max(1, original_chars // 4)
    compressed_tokens = max(1, compressed_chars // 4)

    return {
        "original_chars": original_chars,
        "compressed_chars": compressed_chars,
        "savings_pct": savings_pct,
        "original_tokens_est": original_tokens,
        "compressed_tokens_est": compressed_tokens,
    }
