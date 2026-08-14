import sys
from pathlib import Path
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

SUPERMARKET_PRIVATE_LABELS = [
    "tienda inglesa", "tata", "casino", "leader price", "great value", "el dorado", "disco", "devoto", "geant"
]

CONAPROLE_BRANDS = [
    "polar food", "polar", "colet", "viva", "deleite", "sinfonia", "sinfonía", 
    "conamigos", "blancanube", "baccanal", "conahorro", "lactoplus", "máxima", "maxima", "triffle"
]

def is_valid_match_pair(official_name: str, supermarket_name: str) -> bool:
    off_lower = official_name.lower()
    sup_lower = supermarket_name.lower()

    # 1. Si el producto del supermercado es Marca Propia (ej: Tienda Inglesa) y el oficial es Conaprole / Polar Food -> NO MATCH
    for priv in SUPERMARKET_PRIVATE_LABELS:
        if priv in sup_lower and priv not in off_lower:
            return False

    # 2. Regla de Marcas Conaprole y Licencias (Polar Food, Colet, etc.)
    for brand in CONAPROLE_BRANDS:
        in_off = brand in off_lower
        in_sup = brand in sup_lower
        if in_off != in_sup:
            return False

    return True

off = "Empanadas Polar food queso y aceitunas x 3 unidades"
sup1 = "Empanadas de Queso y Aceitunas TIENDA INGLESA (6 un.) 420 g"
sup2 = "Empanadas Polar Food Queso y Aceitunas x 3 un"

print(f"Oficial: '{off}'")
print(f"vs Sup Marca Propia ('{sup1}'): Válido =", is_valid_match_pair(off, sup1))
print(f"vs Sup Correcto ('{sup2}'): Válido =", is_valid_match_pair(off, sup2))
