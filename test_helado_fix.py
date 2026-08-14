import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CATEGORY_KEYWORDS = {
    "helado": ["helado", "helados"],
    "queso": ["queso", "quesos"],
    "yogur": ["yogur", "yogures"],
    "postre": ["postre", "postres", "flan", "pudding", "pudín"],
    "jugo": ["jugo", "jugos"],
    "manteca": ["manteca"],
    "alfajor": ["alfajor", "alfajores"],
    "gelatina": ["gelatina", "gelatinas"]
}

def is_valid_match_pair(official_name: str, official_cat: str, supermarket_name: str) -> bool:
    off_lower = official_name.lower()
    cat_lower = official_cat.lower()
    sup_lower = supermarket_name.lower()

    # Regla de Tipos de Producto incompatibles (ej. Helado vs Dulce de Leche)
    for cat_key, synonyms in CATEGORY_KEYWORDS.items():
        in_sup = any(s in sup_lower for s in synonyms)
        in_off = any(s in off_lower or s in cat_lower for s in synonyms)
        
        # Si el supermercado dice "Helado" (o Queso, Yogur, etc.) y la ficha oficial NO es Helado -> NO MATCH
        if in_sup and not in_off:
            return False

    return True

off_name = "Dulce Crema de Leche"
off_cat = "Dulce de leche"
sup_name1 = "Helado CONAPROLE súper dulce de leche 250 cc"
sup_name2 = "Dulce de Leche Conaprole Crema 250g"

print(f"Oficial: '{off_name}' (Cat: {off_cat})")
print(f"vs Sup Helado ('{sup_name1}'): Válido =", is_valid_match_pair(off_name, off_cat, sup_name1))
print(f"vs Sup Correcto ('{sup_name2}'): Válido =", is_valid_match_pair(off_name, off_cat, sup_name2))
