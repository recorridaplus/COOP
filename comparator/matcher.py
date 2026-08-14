"""
matcher.py — Motor de matching inteligente entre catálogo Conaprole y supermercados.

Reglas avanzadas:
1. Umbral de similitud de nombre mínimo del 90% (evita asumir que son el mismo producto si no coinciden al 90%).
2. Normalización de nombres para ignorar ruido de unidades.
3. Evaluación paralela ultrarrápida de imágenes (pHash + recorte de lienzo).
4. Clasificación exacta de insignias:
   - 🔴 APOCRYPHAL_IMAGE: Foto casera/propia del CM
   - 🟡 DIFFERENT_IMAGE: Otra versión oficial de la foto
   - 📝 NAME_DISCREPANCY: Redacción del nombre con ligera diferencia
"""

import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent.parent))
from rapidfuzz import fuzz
from comparator.text_comparator import compare_descriptions
from comparator.image_comparator import compare_images

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CONAPROLE_PATH = DATA_DIR / "conaprole_catalog.json"
SUPERMARKETS_DIR = DATA_DIR / "supermarkets"
REPORT_OUTPUT_PATH = DATA_DIR / "latest_comparison_report.json"

SUPERMARKET_PRIVATE_LABELS = [
    "tienda inglesa", "tata", "casino", "leader price", 
    "great value", "el dorado", "disco", "devoto", "geant"
]

CONAPROLE_BRANDS = [
    "polar food", "polar", "colet", "viva", "deleite", "sinfonia", "sinfonía", 
    "conamigos", "blancanube", "baccanal", "conahorro", "lactoplus", 
    "máxima", "maxima", "triffle", "orgullo celeste"
]

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

def normalize_product_name(name: str) -> str:
    text = name.lower()
    text = re.sub(r'\bconaprole\b', '', text)
    text = re.sub(r'\b\d+\s*(ml|cc|g|gr|kg|l|lt|un|unidades)\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_valid_match_pair(official_name: str, official_category: str, supermarket_name: str) -> bool:
    off_lower = official_name.lower()
    cat_lower = (official_category or "").lower()
    sup_lower = supermarket_name.lower()

    for priv in SUPERMARKET_PRIVATE_LABELS:
        if priv in sup_lower and priv not in off_lower:
            return False

    for brand in CONAPROLE_BRANDS:
        in_off = brand in off_lower
        in_sup = brand in sup_lower
        if in_off != in_sup:
            return False

    for cat_key, synonyms in CATEGORY_KEYWORDS.items():
        in_sup = any(s in sup_lower for s in synonyms)
        in_off = any(s in off_lower or s in cat_lower for s in synonyms)
        if in_sup and not in_off:
            return False

    if "colet" in sup_lower and "colet" not in off_lower:
        return False
    if "colet" in off_lower and "colet" not in sup_lower:
        return False

    return True

def calculate_match_score(official_name: str, official_category: str, supermarket_name: str) -> float:
    if not is_valid_match_pair(official_name, official_category, supermarket_name):
        return 0.0

    norm_off = normalize_product_name(official_name)
    norm_sup = normalize_product_name(supermarket_name)

    sort_score = fuzz.token_sort_ratio(norm_off, norm_sup)
    set_score = fuzz.token_set_ratio(norm_off, norm_sup)

    final_score = (sort_score * 0.6) + (set_score * 0.4)
    return round(final_score, 2)

def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def run_matching(compare_images_flag: bool = True, min_match_threshold: float = 90.0) -> dict:
    logger.info(f"🔍 Cargando catálogo oficial de Conaprole (Umbral min similitud: {min_match_threshold}%)...")
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

    candidate_pairs = []
    summary = {sp: {"matches": 0, "discrepancies": 0} for sp in supermarket_catalogs.keys()}

    for sp_name, sp_products in supermarket_catalogs.items():
        if not sp_products:
            continue

        for off_prod in official_products:
            off_name = off_prod["name"]
            off_cat = off_prod.get("category", "")

            best_sp_prod = None
            best_score = 0.0

            for sp_prod in sp_products:
                sp_name_pub = sp_prod.get("name", "")
                if not sp_name_pub:
                    continue

                score = calculate_match_score(off_name, off_cat, sp_name_pub)
                if score > best_score and score >= min_match_threshold:
                    best_score = score
                    best_sp_prod = sp_prod

            if best_sp_prod:
                candidate_pairs.append((sp_name, off_prod, best_sp_prod, best_score))

    logger.info(f"⚡ {len(candidate_pairs)} candidatos con similitud >= {min_match_threshold}%. Evaluando imágenes...")

    # Helper para evaluar imágenes en paralelo
    def _evaluate_image_pair(item):
        sp_name, off_prod, best_sp_prod, score = item
        off_img = off_prod["images"][0] if off_prod.get("images") else ""
        sp_img = best_sp_prod.get("image_url", "")
        img_cmp = None
        if compare_images_flag and off_img and sp_img:
            img_cmp = compare_images(off_img, sp_img)
            if img_cmp and "phash_distance" in img_cmp:
                img_cmp["phash_distance"] = int(img_cmp["phash_distance"])
        return (sp_name, off_prod, best_sp_prod, score, img_cmp)

    if compare_images_flag and candidate_pairs:
        with ThreadPoolExecutor(max_workers=12) as executor:
            evaluated_pairs = list(executor.map(_evaluate_image_pair, candidate_pairs))
    else:
        evaluated_pairs = [(sp_name, off_prod, best_sp_prod, score, None) for sp_name, off_prod, best_sp_prod, score in candidate_pairs]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_official_products": len(official_products),
        "supermarkets_analyzed": list(supermarket_catalogs.keys()),
        "discrepancies": [],
        "matches_summary": summary
    }

    for sp_name, off_prod, best_sp_prod, score, img_cmp in evaluated_pairs:
        off_name = off_prod["name"]
        sp_name_pub = best_sp_prod["name"]

        discrepancy_type = None
        alert_level = None

        if img_cmp and img_cmp["status"] == "APOCRYPHAL_IMAGE":
            discrepancy_type = "APOCRYPHAL_IMAGE"
            alert_level = "RED"
        elif img_cmp and img_cmp["status"] == "DIFFERENT_IMAGE":
            discrepancy_type = "DIFFERENT_IMAGE"
            alert_level = "YELLOW"
        elif score < 96.0:
            discrepancy_type = "NAME_DISCREPANCY"
            alert_level = "BLUE"

        if discrepancy_type:
            summary[sp_name]["discrepancies"] += 1
            report["discrepancies"].append({
                "supermarket": sp_name,
                "conaprole_product": {
                    "id": off_prod["id"],
                    "name": off_name,
                    "category": off_prod.get("category", ""),
                    "image_url": off_prod["images"][0] if off_prod.get("images") else "",
                    "url": off_prod["url"]
                },
                "supermarket_product": {
                    "name": sp_name_pub,
                    "image_url": best_sp_prod.get("image_url", ""),
                    "url": best_sp_prod.get("product_url", "")
                },
                "name_comparison": {
                    "official_name": off_name,
                    "supermarket_name": sp_name_pub,
                    "similarity_score": score
                },
                "description_comparison": compare_descriptions(off_prod.get("description", ""), best_sp_prod.get("description", "")),
                "image_comparison": img_cmp,
                "discrepancy_type": discrepancy_type,
                "alert_level": alert_level
            })
        else:
            summary[sp_name]["matches"] += 1

    report["matches_summary"] = summary

    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Reporte inteligente generado en: {REPORT_OUTPUT_PATH}")
    logger.info(f"   Total discrepancias encontradas: {len(report['discrepancies'])}")
    return report

if __name__ == "__main__":
    run_matching(compare_images_flag=True, min_match_threshold=90.0)
