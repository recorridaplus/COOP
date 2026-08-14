import sys
from pathlib import Path
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

# Lista de marcas/líneas distintivas de Conaprole
SUB_BRANDS = [
    "colet", "viva", "deleite", "sinfonia", "sinfonía", 
    "conamigos", "blancanube", "bio", "clásico", "clasico"
]

def calculate_smart_match_score(official_name: str, supermarket_name: str) -> float:
    off_lower = official_name.lower()
    sup_lower = supermarket_name.lower()
    
    # 1. Regla de sub-marcas distintivas (ej: Colet, Viva, Deleite)
    for sub in SUB_BRANDS:
        in_official = sub in off_lower
        in_supermarket = sub in sup_lower
        # Si la marca está en uno pero NO en el otro -> NO ES EL MISMO PRODUCTO
        if in_official != in_supermarket:
            return 0.0

    # 2. Token Sort Ratio base
    base_score = fuzz.token_sort_ratio(off_lower, sup_lower)
    
    # 3. Token Set Ratio para variaciones de orden de palabras
    set_score = fuzz.token_set_ratio(off_lower, sup_lower)
    
    # Combinación balanceada
    final_score = (base_score * 0.6) + (set_score * 0.4)
    return round(final_score, 2)

# Prueba con el caso reportado por el usuario
off = "Colet Dulce de Leche 250 ml"
sup1 = "Dulce De Leche Conaprole 250Gr ."
sup2 = "Leche Chocolatada Conaprole Colet Dulce De Leche 250 ml"

print(f"Oficial: '{off}'")
print(f"vs Sup Falso ('{sup1}'): Score =", calculate_smart_match_score(off, sup1))
print(f"vs Sup Correcto ('{sup2}'): Score =", calculate_smart_match_score(off, sup2))
