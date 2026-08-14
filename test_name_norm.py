import sys
from pathlib import Path
import re
from rapidfuzz import fuzz, utils

sys.path.insert(0, str(Path(__file__).parent.parent))

def normalize_product_name(name: str) -> str:
    """
    Normaliza el nombre removiendo prefijos de marca genéricos y unidades comunes.
    """
    text = name.lower()
    # Remover la palabra 'conaprole'
    text = re.sub(r'\bconaprole\b', '', text)
    # Normalizar unidades comunes (ml, cc, g, gr, kg, lt, l, un, cc.)
    text = re.sub(r'\b\d+\s*(ml|cc|g|gr|kg|l|lt|un|unidades)\b', '', text)
    # Limpiar espacios dobles
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compare_names_smart(off_name: str, sup_name: str) -> float:
    norm_off = normalize_product_name(off_name)
    norm_sup = normalize_product_name(sup_name)

    sort_score = fuzz.token_sort_ratio(norm_off, norm_sup)
    set_score = fuzz.token_set_ratio(norm_off, norm_sup)

    return round((sort_score * 0.6) + (set_score * 0.4), 2)

off = "Yogur Con Fondo de Durazno"
sup = "Yogur CONAPROLE Fondo Durazno 180 cc"

print("Nombre Oficial:", off)
print("Nombre Super  :", sup)
print("Normalizado Oficial:", normalize_product_name(off))
print("Normalizado Super  :", normalize_product_name(sup))
print("Score Normalizado:", compare_names_smart(off, sup))
