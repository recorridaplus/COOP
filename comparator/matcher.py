"""
matcher.py — Motor de matching inteligente entre catálogo Conaprole y supermercados.

Reglas avanzadas:
1. Si la imagen coincide (status == 'MATCH', pHash <= 12) y el nombre es compatible (>= 90%), es una COINCIDENCIA PERFECTA (no genera discrepancia).
2. Discrepancias reales reportadas:
   - 🔴 APOCRYPHAL_IMAGE: Foto casera/propia tomada en tienda por el CM.
   - 🟡 DIFFERENT_IMAGE: Foto de catálogo pero otra versión/diseño diferente.
   - 📝 NAME_DISCREPANCY: Nombre con baja similitud sin coincidencia de foto.
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
from comparator.ai_verifier import is_openai_available, verify_product_match_with_ai

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

SUBBRAND_CANONICAL = {
    "polar food": "polar",
    "polar": "polar",
    "colet": "colet",
    "viva": "viva",
    "deleite": "deleite",
    "sinfonia": "sinfonia",
    "sinfonía": "sinfonia",
    "conamigos": "conamigos",
    "blancanube": "blancanube",
    "baccanal": "baccanal",
    "conahorro": "conahorro",
    "lactoplus": "lactoplus",
    "máxima": "maxima",
    "maxima": "maxima",
    "triffle": "triffle",
    "orgullo celeste": "orgullo celeste"
}

def get_subbrands(text: str) -> set[str]:
    found = set()
    text_lower = text.lower()
    for raw, canonical in SUBBRAND_CANONICAL.items():
        if re.search(r'\b' + re.escape(raw) + r'\b', text_lower):
            found.add(canonical)
    return found

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

def extract_presentation(name: str) -> dict | None:
    text = name.lower()
    
    match_l = re.search(r'(\d+(?:[.,]\d+)?)\s*(l|lt|litro|litros)\b', text)
    if match_l:
        val = float(match_l.group(1).replace(',', '.'))
        return {"type": "volume_ml", "value": int(val * 1000)}
        
    match_ml = re.search(r'(\d+)\s*(ml|cc|cc\.)\b', text)
    if match_ml:
        return {"type": "volume_ml", "value": int(match_ml.group(1))}

    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|kilo|kilos)\b', text)
    if match_kg:
        val = float(match_kg.group(1).replace(',', '.'))
        return {"type": "weight_g", "value": int(val * 1000)}

    match_g = re.search(r'(\d+)\s*(g|gr|gramos|grs)\b', text)
    if match_g:
        return {"type": "weight_g", "value": int(match_g.group(1))}

    match_un = re.search(r'(?:x\s*(\d+)|(\d+)\s*un\b|(\d+)\s*unidades\b)', text)
    if match_un:
        val = match_un.group(1) or match_un.group(2) or match_un.group(3)
        return {"type": "units", "value": int(val)}

    return None

def are_presentations_compatible(official_name: str, supermarket_name: str) -> bool:
    p_off = extract_presentation(official_name)
    p_sup = extract_presentation(supermarket_name)

    if p_off and p_sup:
        if p_off["type"] == p_sup["type"]:
            return p_off["value"] == p_sup["value"]
    return True

def normalize_product_name(name: str) -> str:
    text = name.lower()
    text = re.sub(r'\bconaprole\b', '', text)
    for raw in SUBBRAND_CANONICAL.keys():
        text = re.sub(r'\b' + re.escape(raw) + r'\b', '', text)
    text = re.sub(r'\b\d+\s*(ml|cc|g|gr|kg|l|lt|un|unidades)\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

LACTOSE_KEYWORDS = ["deslactosada", "sin lactosa", "zero lactosa", "0% lactosa"]
FAT_KEYWORDS = {
    "descremada": ["descremada", "skimm"],
    "semidescremada": ["semidescremada", "semi-descremada", "semi descremada"],
    "entera": ["entera"]
}
SALT_KEYWORDS = {
    "sin_sal": ["sin sal", "unsalted"],
    "con_sal": ["con sal", "salted"]
}
FLAVOR_KEYWORDS = [
    "durazno", "frutilla", "vainilla", "chocolate", "manzana", "naranja", 
    "anana", "ananá", "multifruta", "dulce de leche", "menta", "banana", 
    "maracuya", "maracuyá", "ciruela", "pera", "uva", "frutos rojos"
]

def check_feature_incompatibility(off_name: str, sup_name: str) -> bool:
    """Devuelve True si hay incompatibilidad crítica de atributos (ej. Deslactosada vs Normal)."""
    off_lower = off_name.lower()
    sup_lower = sup_name.lower()

    # 1. Lactosa (ej. Deslactosada vs Normal)
    off_has_deslac = any(k in off_lower for k in LACTOSE_KEYWORDS)
    sup_has_deslac = any(k in sup_lower for k in LACTOSE_KEYWORDS)
    if off_has_deslac != sup_has_deslac:
        return True

    # 2. Tipo de materia grasa (Descremada vs Entera vs Semidescremada)
    def get_fat_type(text):
        for fat_type, kw_list in FAT_KEYWORDS.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in kw_list):
                return fat_type
        return None

    fat_off = get_fat_type(off_lower)
    fat_sup = get_fat_type(sup_lower)
    if fat_off and fat_sup and fat_off != fat_sup:
        return True

    # 3. Sal (Con sal vs Sin sal)
    def get_salt_type(text):
        for salt_type, kw_list in SALT_KEYWORDS.items():
            if any(kw in text for kw in kw_list):
                return salt_type
        return None

    salt_off = get_salt_type(off_lower)
    salt_sup = get_salt_type(sup_lower)
    if salt_off and salt_sup and salt_off != salt_sup:
        return True
    if (salt_off == "sin_sal" and not salt_sup) or (salt_sup == "sin_sal" and not salt_off):
        return True

    # 4. Sabores (Durazno vs Frutilla, etc.)
    def get_flavors(text):
        found = set()
        for fl in FLAVOR_KEYWORDS:
            if re.search(r'\b' + re.escape(fl) + r'\b', text):
                found.add(fl.replace("ananá", "anana").replace("maracuyá", "maracuya"))
        return found

    flav_off = get_flavors(off_lower)
    flav_sup = get_flavors(sup_lower)
    if flav_off and flav_sup and flav_off != flav_sup:
        return True
    if (flav_off and not flav_sup) or (flav_sup and not flav_off):
        return True

    return False

def is_valid_match_pair(official_name: str, official_category: str, supermarket_name: str) -> bool:
    off_lower = official_name.lower()
    cat_lower = (official_category or "").lower()
    sup_lower = supermarket_name.lower()

    if check_feature_incompatibility(official_name, supermarket_name):
        return False

    if not are_presentations_compatible(official_name, supermarket_name):
        return False

    for priv in SUPERMARKET_PRIVATE_LABELS:
        if priv in sup_lower and priv not in off_lower:
            return False

    off_sub = get_subbrands(off_lower)
    sup_sub = get_subbrands(sup_lower)

    if off_sub and sup_sub and off_sub != sup_sub:
        return False

    if sup_sub and not off_sub:
        return False

    for cat_key, synonyms in CATEGORY_KEYWORDS.items():
        in_sup = any(s in sup_lower for s in synonyms)
        in_off = any(s in off_lower or s in cat_lower for s in synonyms)
        if in_sup and not in_off:
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

def run_matching(compare_images_flag: bool = True, min_match_threshold: float = 90.0, use_ai_flag: bool = True) -> dict:
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

    logger.info(f"⚡ {len(candidate_pairs)} candidatos válidos por presentación y nombre (>= {min_match_threshold}%). Evaluando imágenes...")

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

    ai_active = use_ai_flag and is_openai_available()
    if ai_active:
        logger.info("🤖 OpenAI Vision activado para auditar candidatos y packagings.")
    else:
        logger.info("ℹ️ OpenAI Vision omitido (sin API Key o bandera en False). Funcionando en modo motor local.")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_official_products": len(official_products),
        "supermarkets_analyzed": list(supermarket_catalogs.keys()),
        "ai_enabled": ai_active,
        "discrepancies": [],
        "matches_summary": summary
    }

    for sp_name, off_prod, best_sp_prod, score, img_cmp in evaluated_pairs:
        off_name = off_prod["name"]
        sp_name_pub = best_sp_prod["name"]

        discrepancy_type = None
        alert_level = None
        ai_result = None

        if ai_active:
            logger.info(f"   🤖 Consultando OpenAI Vision para '{off_name}' vs '{sp_name_pub}'...")
            ai_result = verify_product_match_with_ai(off_prod, best_sp_prod, img_cmp)
            
            if ai_result.get("status") == "SUCCESS":
                # Si la IA determina que NO es el mismo producto, descartar falsa coincidencia
                if ai_result.get("is_same_product") is False:
                    logger.info(f"   ❌ IA rechazó el match: {ai_result.get('explanation')}")
                    continue

                # Si es el mismo producto
                verdict = ai_result.get("ai_verdict")
                if verdict == "MATCH" and ai_result.get("is_same_presentation"):
                    summary[sp_name]["matches"] += 1
                    continue
                elif verdict in ["PACKAGING_REDESIGN", "DIFFERENT_IMAGE"]:
                    discrepancy_type = "DIFFERENT_IMAGE"
                    alert_level = "YELLOW"
                elif verdict == "APOCRYPHAL_IMAGE":
                    discrepancy_type = "APOCRYPHAL_IMAGE"
                    alert_level = "RED"
                elif verdict == "DIFFERENT_PRESENTATION":
                    discrepancy_type = "NAME_DISCREPANCY"
                    alert_level = "BLUE"

        if not discrepancy_type:
            if img_cmp and img_cmp["status"] == "APOCRYPHAL_IMAGE":
                discrepancy_type = "APOCRYPHAL_IMAGE"
                alert_level = "RED"
            elif img_cmp and img_cmp["status"] == "DIFFERENT_IMAGE":
                discrepancy_type = "DIFFERENT_IMAGE"
                alert_level = "YELLOW"
            elif img_cmp and img_cmp["status"] == "MATCH":
                # Misma imagen/envase verificado por pHash -> Es coincidencia perfecta
                summary[sp_name]["matches"] += 1
                continue
            elif not img_cmp and score < 95.0:
                discrepancy_type = "NAME_DISCREPANCY"
                alert_level = "BLUE"
            else:
                summary[sp_name]["matches"] += 1
                continue

        if discrepancy_type:
            summary[sp_name]["discrepancies"] += 1
            
            discrepancy_item = {
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
            }

            if ai_result:
                discrepancy_item["ai_verification"] = ai_result

            report["discrepancies"].append(discrepancy_item)

    report["matches_summary"] = summary

    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Reporte inteligente generado en: {REPORT_OUTPUT_PATH}")
    logger.info(f"   Total discrepancias encontradas: {len(report['discrepancies'])}")
    return report

if __name__ == "__main__":
    run_matching(compare_images_flag=True, min_match_threshold=90.0, use_ai_flag=True)


