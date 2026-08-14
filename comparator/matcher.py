"""
matcher.py — Motor de matching inteligente entre catálogo Conaprole y supermercados.

Reglas avanzadas de matching:
1. Filtrado por sub-marca distintiva (Colet, Viva, Deleite, Sinfonía, Conamigos, etc.)
   Si un producto oficial tiene "Colet", el producto del supermercado DEBE contener "Colet".
2. Regla de compatibilidad de categoría/tipo (Queso vs Dulce de Leche vs Leche).
3. Score ponderado de similitud token-sort + token-set.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from rapidfuzz import fuzz
from comparator.text_comparator import compare_names, compare_descriptions
from comparator.image_comparator import compare_images

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CONAPROLE_PATH = DATA_DIR / "conaprole_catalog.json"
SUPERMARKETS_DIR = DATA_DIR / "supermarkets"
REPORT_OUTPUT_PATH = DATA_DIR / "latest_comparison_report.json"

# Sub-marcas y líneas de producto distintivas de Conaprole
SUB_BRANDS = [
    "colet", "viva", "deleite", "sinfonia", "sinfonía", 
    "conamigos", "blancanube", "baccanal", "conahorro",
    "lactoplus", "máxima", "maxima", "triffle"
]

# Tipos de producto primarios para evitar cruces (ej: Dulce de leche vs Bebida/Leche)
PRODUCT_TYPES = [
    "dulce de leche", "leche", "queso", "yogur", "helado", 
    "postre", "jugo", "manteca", "crema", "alfajor", "gelatina"
]

def is_valid_match_pair(official_name: str, supermarket_name: str) -> bool:
    """
    Verifica si un par de nombres es un candidato válido antes de calcular score.
    Previene falsos positivos como 'Colet Dulce de Leche' vs 'Dulce de Leche Conaprole'.
    """
    off_lower = official_name.lower()
    sup_lower = supermarket_name.lower()

    # 1. Regla de sub-marcas (Colet, Viva, Deleite, etc.)
    for sub in SUB_BRANDS:
        in_off = sub in off_lower
        in_sup = sub in sup_lower
        if in_off != in_sup:
            return False  # Uno tiene la sub-marca y el otro no -> FALSO MATCH

    # 2. Regla de tipo de producto primario
    # Si el producto oficial es "Dulce de Leche" (pote) y no Colet, no emparejar con Colet
    if "colet" in sup_lower and "colet" not in off_lower:
        return False
    if "colet" in off_lower and "colet" not in sup_lower:
        return False

    return True

def calculate_match_score(official_name: str, supermarket_name: str) -> float:
    """Calcula score ponderado de similitud entre dos nombres de producto."""
    if not is_valid_match_pair(official_name, supermarket_name):
        return 0.0

    off_lower = official_name.lower()
    sup_lower = supermarket_name.lower()

    sort_score = fuzz.token_sort_ratio(off_lower, sup_lower)
    set_score = fuzz.token_set_ratio(off_lower, sup_lower)

    # Score ponderado: da peso tanto al orden como a la presencia de tokens clave
    final_score = (sort_score * 0.65) + (set_score * 0.35)
    return round(final_score, 2)

def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def run_matching(compare_images_flag: bool = True, min_match_threshold: float = 65.0) -> dict:
    """
    Ejecuta el proceso inteligente de matching y comparación.
    """
    logger.info("🔍 Cargando catálogo oficial de Conaprole...")
    conaprole_data = load_json(CONAPROLE_PATH)
    if not conaprole_data:
        raise FileNotFoundError(f"No se encontró {CONAPROLE_PATH}. Ejecuta el scraper de Conaprole primero.")

    official_products = conaprole_data.get("products", [])
    logger.info(f"   {len(official_products)} productos oficiales cargados.")

    supermarket_files = list(SUPERMARKETS_DIR.glob("*.json"))
    supermarket_catalogs = {}
    for sp_file in supermarket_files:
        sp_data = load_json(sp_file)
        if sp_data and sp_data.get("products"):
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
        discrepancies_count = 0
        matches_count = 0

        for off_prod in official_products:
            off_name = off_prod["name"]
            off_img = off_prod["images"][0] if off_prod.get("images") else ""

            # Buscar el MEJOR match candidato en el supermercado usando nuestras reglas inteligentes
            best_sp_prod = None
            best_score = 0.0

            for sp_prod in sp_products:
                sp_name_pub = sp_prod.get("name", "")
                if not sp_name_pub:
                    continue

                score = calculate_match_score(off_name, sp_name_pub)
                if score > best_score and score >= min_match_threshold:
                    best_score = score
                    best_sp_prod = sp_prod

            if not best_sp_prod:
                # No se encontró equivalente válido para este producto en este supermercado
                continue

            sp_name_pub = best_sp_prod["name"]
            sp_img = best_sp_prod.get("image_url", "")

            # Comparar nombres
            name_cmp = compare_names(off_name, sp_name_pub)
            name_cmp["similarity_score"] = best_score # Usar score inteligente

            # Comparar descripción
            desc_cmp = compare_descriptions(off_prod.get("description", ""), best_sp_prod.get("description", ""))

            # Comparar imágenes (si corresponde)
            img_cmp = None
            if compare_images_flag and off_img and sp_img:
                img_cmp = compare_images(off_img, sp_img)

            # Determinar discrepancias
            has_name_discrepancy = best_score < 90.0
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
                        "name": sp_name_pub,
                        "image_url": sp_img,
                        "url": best_sp_prod.get("product_url", "")
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

    logger.info(f"\n✅ Reporte inteligente generado en: {REPORT_OUTPUT_PATH}")
    logger.info(f"   Total discrepancias válidas encontradas: {len(report['discrepancies'])}")
    return report

if __name__ == "__main__":
    run_matching(compare_images_flag=False)
