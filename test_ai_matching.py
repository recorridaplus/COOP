"""
test_ai_matching.py — Test de verificación para la integración de OpenAI Vision.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comparator.ai_verifier import is_openai_available, verify_product_match_with_ai
from comparator.matcher import run_matching

def test_ai_verifier_fallback():
    print("--- 1. Probando verificación de disponibilidad de API ---")
    available = is_openai_available()
    print(f"OpenAI API disponible en entorno: {available}")

    off_prod = {
        "id": "producto-leche-leche-ultra-extra-calcio-semidescremada",
        "name": "Leche Semidescremada Extra Calcio 1L",
        "category": "Leches",
        "description": "Leche semidescremada pasteurizada, calcio lácteo, vitaminas E, A y D3.",
        "images": ["https://cdn.conaprole.uy/gallery/202201/20241130193553_1717833505.png"],
        "url": "https://www.conaprole.uy/producto/producto-leche-leche-ultra-extra-calcio-semidescremada/"
    }

    sp_prod = {
        "name": "Leche Conaprole Semidescremada Extra Calcio Sachet 1L",
        "description": "Leche Conaprole Semidescremada 1 litro extra calcio",
        "image_url": "https://cdn.conaprole.uy/gallery/202201/20241130193553_1717833505.png",
        "product_url": "https://tiendainglesa.com.uy/producto/123"
    }

    print("\n--- 2. Probando respuesta del módulo ai_verifier con OpenAI Vision real ---")
    res = verify_product_match_with_ai(off_prod, sp_prod)
    print(f"Respuesta del módulo AI: {res}")
    assert res.get("status") == "SUCCESS", f"La llamada a la IA falló: {res}"


def test_run_matching_dry_run():
    print("\n--- 3. Probando ejecucion de run_matching sin descarga pesada de imagenes ---")
    report = run_matching(compare_images_flag=False, min_match_threshold=90.0, use_ai_flag=False)
    print(f"Reporte generado exitosamente con {len(report.get('discrepancies', []))} discrepancias.")
    assert "matches_summary" in report

if __name__ == "__main__":
    test_ai_verifier_fallback()
    test_run_matching_dry_run()
    print("\n[OK] Todos los tests del modulo AI pasaron correctamente.")

