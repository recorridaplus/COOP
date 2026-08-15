import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comparator.matcher import is_valid_match_pair, calculate_match_score, normalize_product_name

def test_subbrand_cases():
    test_cases = [
        # (official, category, supermarket, expected_valid)
        ("Blancanube Leche Descremada", "Leches", "Blancanube Leche Descremada 1 L", True),
        ("Blancanube Leche Descremada", "Leches", "Leche Descremada Conaprole 1 L", True),
        ("Blancanube Leche Descremada", "Leches", "Yogur Viva Descremado 1 L", False),
        ("Empanadas Polar food queso y aceitunas x 3 unidades", "Congelados", "Empanadas Polar Food Queso y Aceitunas x 3 un", True),
        ("Empanadas Polar food queso y aceitunas x 3 unidades", "Congelados", "Empanadas Conaprole Queso y Aceitunas x 3 un", True),
        ("Empanadas Polar food queso y aceitunas x 3 unidades", "Congelados", "Empanadas Colet Queso y Aceitunas x 3 un", False),
        ("Empanadas Polar food queso y aceitunas x 3 unidades", "Congelados", "Empanadas de Queso TIENDA INGLESA 420g", False),
        ("Colet Clásico 1L", "Leches", "Colet Clásico 1 L", True),
        ("Colet Clásico 1L", "Leches", "Deleite Dulce de Leche 1 L", False),
        ("Leche Fresca Conaprole Descremada 1 L", "Leches", "Leche fresca CONAPROLE descremada 1 L", True),
        ("Leche Fresca Conaprole Descremada 1 L", "Leches", "Colet Clásico 1 L", False),
    ]

    all_passed = True
    for off, cat, sup, exp in test_cases:
        valid = is_valid_match_pair(off, cat, sup)
        score = calculate_match_score(off, cat, sup) if valid else 0.0
        status = "PASSED" if valid == exp else "FAILED"
        if valid != exp:
            all_passed = False
        print(f"[{status}] Oficial: '{off}' vs Sup: '{sup}' -> Valid: {valid} (Exp: {exp}), Score: {score}")

    if all_passed:
        print("\n[OK] TODAS LAS PRUEBAS DE SUBMARCAS PASARON CORRECTAMENTE.")
    else:
        print("\n[ERROR] ALGUNAS PRUEBAS FALLARON.")

if __name__ == "__main__":
    test_subbrand_cases()
