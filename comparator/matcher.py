"""
matcher.py — Motor de matching y comparación entre catálogo Conaprole y supermercados.

Recorre el catálogo de Conaprole (conaprole_catalog.json) y los datos de cada
supermercado (data/supermarkets/*.json), empareja productos por nombre (fuzzy matching),
ejecuta las comparaciones de texto e imágenes, y genera un reporte unificado.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from rapidfuzz import fuzz, process
from comparator.text_comparator import compare_names, compare_descriptions
from comparator.image_comparator import compare_images

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CONAPROLE_PATH = DATA_DIR / "conaprole_catalog.json"
SUPERMARKETS_DIR = DATA_DIR / "supermarkets"
REPORT_OUTPUT_PATH = DATA_DIR / "latest_comparison_report.json"

def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def run_matching(compare_images_flag: bool = True) -> dict:
    """
    Ejecuta el proceso completo de matching y comparación.
    """
    logger.info("🔍 Cargando catálogo oficial de Conaprole...")
    conaprole_data = load_json(CONAPROLE_PATH)
    if not conaprole_data:
        raise FileNotFoundError(f"No se encontró {CONAPROLE_PATH}. Ejecuta el scraper de Conaprole primero.")

    official_products = conaprole_data.get("products", [])
    logger.info(f"   {len(official_products)} productos oficiales cargados.")

    # Cargar archivos de supermercados
    supermarket_files = list(SUPERMARKETS_DIR.glob("*.json"))
    if not supermarket_files:
        logger.warning(f"⚠️  No hay archivos JSON en {SUPERMARKETS_DIR}")

    supermarket_catalogs = {}
    for sp_file in supermarket_files:
        sp_data = load_json(sp_file)
        if sp_data:
            sp_name = sp_data.get("supermarket", sp_file.stem)
            supermarket_catalogs[sp_name] = sp_data.get("products", [])
            logger.info(f"   {sp_name}: {len(supermarket_catalogs[sp_name])} productos cargados.")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_official_products": len(official_products),
        "supermarkets_analyzed": list(supermarket_catalogs.keys()),
        "discrepancies": [],
        "matches_summary": {}
    }

    for sp_name, sp_products in supermarket_catalogs.items():
        if not sp_products:
            continue

        logger.info(f"\n⚡ Comparando contra {sp_name}...")
        
        # Crear índice de nombres de supermercado para rapidfuzz
        sp_names = [p["name"] for p in sp_products if p.get("name")]

        discrepancies_count = 0
        matches_count = 0

        for off_prod in official_products:
            off_name = off_prod["name"]
            off_img = off_prod["images"][0] if off_prod.get("images") else ""

            # Buscar el producto equivalente en el supermercado con fuzzy matching
            match_res = process.extractOne(off_name, sp_names, scorer=fuzz.token_sort_ratio)
            if not match_res or match_res[1] < 60:
                # No se encontró el producto en el supermercado
                continue

            best_sp_name, score, idx = match_res
            sp_prod = sp_products[idx]
            sp_img = sp_prod.get("image_url", "")

            # Comparar nombres
            name_cmp = compare_names(off_name, best_sp_name)
            
            # Comparar descripción
            desc_cmp = compare_descriptions(off_prod.get("description", ""), sp_prod.get("description", ""))

            # Comparar imágenes (si está activado y ambas URLs existen)
            img_cmp = None
            if compare_images_flag and off_img and sp_img:
                img_cmp = compare_images(off_img, sp_img)

            # Determinar si hay alguna discrepancia importante
            has_name_discrepancy = name_cmp["similarity_score"] < 85
            has_img_discrepancy = img_cmp and img_cmp["status"] in ["DIFFERENT_IMAGE", "APOCRYPHAL_IMAGE"]

            if has_name_discrepancy or has_img_discrepancy:
                discrepancies_count += 1
                item_discrepancy = {
                    "supermarket": sp_name,
                    "conaprole_product": {
                        "id": off_prod["id"],
                        "name": off_name,
                        "category": off_prod["category"],
                        "image_url": off_img,
                        "url": off_prod["url"]
                    },
                    "supermarket_product": {
                        "name": best_sp_name,
                        "image_url": sp_img,
                        "url": sp_prod.get("product_url", "")
                    },
                    "name_comparison": name_cmp,
                    "description_comparison": desc_cmp,
                    "image_comparison": img_cmp,
                    "alert_level": "RED" if (img_cmp and img_cmp["status"] == "APOCRYPHAL_IMAGE") else "YELLOW"
                }
                report["discrepancies"].append(item_discrepancy)
            else:
                matches_count += 1

        report["matches_summary"][sp_name] = {
            "matches": matches_count,
            "discrepancies": discrepancies_count
        }

    # Guardar reporte
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Reporte generado en: {REPORT_OUTPUT_PATH}")
    logger.info(f"   Total discrepancias encontradas: {len(report['discrepancies'])}")
    return report

if __name__ == "__main__":
    run_matching(compare_images_flag=False) # flag False para prueba rápida sin descargas masivas
