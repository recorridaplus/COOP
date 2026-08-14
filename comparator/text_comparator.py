"""
text_comparator.py — Comparación de texto (nombres y descripciones).

Calcula similitud de strings (0-100) y detecta diferencias clave.
"""

from rapidfuzz import fuzz, utils

def compare_names(official_name: str, supermarket_name: str) -> dict:
    """
    Compara el nombre oficial de Conaprole vs. el publicado por el supermercado.
    
    Devuelve:
    {
        "similarity_score": float (0-100),
        "is_exact_match": bool,
        "official_name": str,
        "supermarket_name": str
    }
    """
    if not official_name or not supermarket_name:
        return {
            "similarity_score": 0.0,
            "is_exact_match": False,
            "official_name": official_name or "",
            "supermarket_name": supermarket_name or ""
        }

    # Normalizar para ignorar mayúsculas y acentos
    norm_off = utils.default_process(official_name)
    norm_sup = utils.default_process(supermarket_name)

    score = fuzz.token_sort_ratio(norm_off, norm_sup)

    return {
        "similarity_score": round(score, 2),
        "is_exact_match": norm_off == norm_sup,
        "official_name": official_name,
        "supermarket_name": supermarket_name
    }

def compare_descriptions(official_desc: str, supermarket_desc: str) -> dict:
    """
    Compara la descripción/ingredientes de Conaprole vs. el supermercado.
    """
    if not official_desc and not supermarket_desc:
        return {"similarity_score": 100.0, "status": "both_empty"}
    if not supermarket_desc:
        return {"similarity_score": 0.0, "status": "supermarket_missing"}
    if not official_desc:
        return {"similarity_score": 100.0, "status": "official_missing"}

    score = fuzz.token_set_ratio(official_desc, supermarket_desc)
    return {
        "similarity_score": round(score, 2),
        "status": "compared"
    }
