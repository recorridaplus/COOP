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
        "id": "test_1",
        "name": "Colet Dulce de Leche 1L",
        "category": "Bebidas Lácteas",
        "description": "Bebida láctea Colet sabor Dulce de Leche tetra pak 1 litro.",
        "images": ["https://conaprole.uy/wp-content/uploads/2020/05/colet-ddl-1l.png"],
        "url": "https://conaprole.uy/producto/colet-ddl-1l"
    }

    sp_prod = {
        "name": "Colet Dulce de Leche Tetra 1000ml",
        "description": "Colet dulce de leche 1L",
        "image_url": "https://tiendainglesa.com.uy/images/colet.png",
        "product_url": "https://tiendainglesa.com.uy/producto/123"
    }

    print("\n--- 2. Probando respuesta del módulo ai_verifier ---")
    res = verify_product_match_with_ai(off_prod, sp_prod)
    print(f"Respuesta del módulo: {res}")
    assert "status" in res, "La respuesta debe incluir el campo 'status'."

def test_run_matching_dry_run():
    print("\n--- 3. Probando ejecucion de run_matching sin descarga pesada de imagenes ---")
    report = run_matching(compare_images_flag=False, min_match_threshold=90.0, use_ai_flag=False)
    print(f"Reporte generado exitosamente con {len(report.get('discrepancies', []))} discrepancias.")
    assert "matches_summary" in report

if __name__ == "__main__":
    test_ai_verifier_fallback()
    test_run_matching_dry_run()
    print("\n[OK] Todos los tests del modulo AI pasaron correctamente.")

