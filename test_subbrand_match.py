import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comparator.matcher import get_subbrands, is_valid_match_pair

test_pairs = [
    ("Deleite Dulce de Leche", "Postres", "Dulce De Leche Conaprole 250Gr ."),
    ("Máxima Dulce de Leche", "Helados", "Dulce De Leche Conaprole 250Gr ."),
    ("Colet Dulce de Leche 1L", "Leches", "Leche Entera Conaprole 1L"),
    ("Dulce de Leche Clásico 970g", "Dulce de leche", "Dulce De Leche Conaprole 970g"),
    ("Deleite Dulce de Leche", "Postres", "Postre Deleite Dulce de Leche Conaprole"),
]

print("--- Evaluación de pares con sub-marcas ---")
for off, cat, sup in test_pairs:
    off_sub = get_subbrands(off)
    sup_sub = get_subbrands(sup)
    
    # Aplicar regla bidireccional
    valid = is_valid_match_pair(off, cat, sup)
    print(f"Oficial : '{off}' (sub: {off_sub})")
    print(f"Super   : '{sup}' (sub: {sup_sub})")
    print(f"Resultado Match Válido: {valid}")
    print("-" * 50)
