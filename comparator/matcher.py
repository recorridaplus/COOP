"""
matcher.py — Motor de matching inteligente entre el catálogo oficial de Conaprole
y las publicaciones capturadas de los supermercados (El Dorado, TATA, Tienda Inglesa, Devoto, Disco, Géant).

Reglas de Negocio:
1. Similitud mínima de nombre configurable (default 90.0%).
2. Exclusión de Marcas Propias de supermercados.
3. Exclusión por coincidencia estricta de Submarcas (ej: Colet, Viva, Deleite, Biotop, Alpazul, etc.).
4. Compatibilidad de Presentación/Volumen (ml vs l, g vs kg).
5. Incompatibilidad de Atributos Críticos (Lactosa, Materia Grasa, Sal, Sabores).
6. Clasificación de Discrepancias de Imagen:
   - APOCRYPHAL_IMAGE (Roja): Packaging alterado o de otra marca.
   - DIFFERENT_IMAGE (Amarilla): Rediseño de packaging o ángulo diferente.
   - NAME_DISCREPANCY (Azul): Nombre con diferencias significativas.
7. Soporte para auditoría visual opcional con OpenAI Vision.
8. Registro de coincidencias verificadas (matches_list) para validación de efectividad.
"""

import json
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

try:
    from rapidfuzz import fuzz
except ImportError:
    from fuzzywuzzy import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))
from comparator.image_comparator import compare_images
from comparator.ai_verifier import verify_product_match_with_ai, is_openai_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CONAPROLE_PATH = DATA_DIR / "conaprole_catalog.json"
SUPERMARKETS_DIR = DATA_DIR / "supermarkets"
OUTPUT_REPORT_PATH = DATA_DIR / "latest_comparison_report.json"

SUPERMARKET_PRIVATE_LABELS = [
    "casino", "ta-ta", "tata", "el clon", "kinko", "frog",
    "leader price", "qualita", "bell's", "great value"
]

SUBBRAND_CANONICAL = {
    "colet": "colet",
    "viva": "viva",
    "deleite": "deleite",
    "polar food": "polar",
    "polar": "polar",
    "blancanube": "blancanube",
    "conamigos": "conamigos",
    "biotop": "biotop",
    "alpazul": "alpazul",
    "magretto": "magretto",
    "sinfonia": "sinfonia",
    "sinfonía": "sinfonia",
    "máxima": "maxima",
    "maxima": "maxima",
    "triffle": "triffle",
    "alpa": "alpa",
    "lactolate": "lactolate",
    "lactoplus": "lactoplus",
    "conacrem": "conacrem",
    "conahorro": "conahorro",
    "baccanal": "baccanal",
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

    # 1. Lactosa
    off_has_deslac = any(k in off_lower for k in LACTOSE_KEYWORDS)
    sup_has_deslac = any(k in sup_lower for k in LACTOSE_KEYWORDS)
    if off_has_deslac != sup_has_deslac:
        return True

    # 2. Materia Grasa
    def get_fat_type(text):
        for fat_type, kw_list in FAT_KEYWORDS.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in kw_list):
                return fat_type
        return None

    fat_off = get_fat_type(off_lower)
    fat_sup = get_fat_type(sup_lower)
    if fat_off and fat_sup and fat_off != fat_sup:
        return True

    # 3. Sal
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

    # 4. Sabores
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

    # Si alguna de las partes menciona una submarca, la otra DEBE pertenecer a la misma submarca
    if (off_sub or sup_sub) and off_sub != sup_sub:
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

def compare_descriptions(official_desc: str, supermarket_desc: str) -> dict:
    if not official_desc or not supermarket_desc:
        return {"has_discrepancy": False, "official_desc": official_desc, "supermarket_desc": supermarket_desc}
    
    score = fuzz.token_set_ratio(official_desc.lower(), supermarket_desc.lower())
    return {
        "has_discrepancy": score < 70,
        "similarity_score": score,
        "official_desc": official_desc,
        "supermarket_desc": supermarket_desc
    }

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

    def _eval_pair_full(item):
        sp_name, off_prod, best_sp_prod, score, img_cmp = item
        off_name = off_prod["name"]
        sp_name_pub = best_sp_prod["name"]

        ai_result = None
        discrepancy_type = None
        alert_level = None

        # 1. Si la imagen es idéntica por pHash (distancia <= 12, MATCH), es COINCIDENCIA PERFECTA
        if img_cmp and img_cmp.get("status") == "MATCH":
            discrepancy_type = None
        # 2. Si el comparador de imágenes detectó una imagen diferente de catálogo (rediseño pHash > 12)
        elif img_cmp and img_cmp.get("status") == "DIFFERENT_IMAGE":
            discrepancy_type = "DIFFERENT_IMAGE"
            alert_level = "YELLOW"
        # 3. Si el comparador de imágenes detectó una foto no oficial / apócrifa (fondo de tienda)
        elif img_cmp and img_cmp.get("status") == "APOCRYPHAL_IMAGE":
            discrepancy_type = "APOCRYPHAL_IMAGE"
            alert_level = "RED"
        elif not img_cmp and score < 95.0:
            discrepancy_type = "NAME_DISCREPANCY"
            alert_level = "BLUE"

        # 4. Si la IA está activa y hay una discrepancia o falta imagen, consultar para auditar/descartar
        if ai_active and (discrepancy_type or not img_cmp):
            logger.info(f"   🤖 Consultando OpenAI Vision para '{off_name}' vs '{sp_name_pub}'...")
            ai_result = verify_product_match_with_ai(off_prod, best_sp_prod, img_cmp)
            
            if ai_result.get("status") == "SUCCESS":
                # Si la IA determina que son productos incompatibles, rechazar el match falso
                if ai_result.get("is_same_product") is False:
                    logger.info(f"   ❌ IA rechazó el match: {ai_result.get('explanation')}")
                    return ("REJECTED", sp_name, None)

                verdict = ai_result.get("ai_verdict")
                if verdict == "APOCRYPHAL_IMAGE":
                    discrepancy_type = "APOCRYPHAL_IMAGE"
                    alert_level = "RED"
                elif verdict in ["PACKAGING_REDESIGN", "DIFFERENT_IMAGE"]:
                    discrepancy_type = "DIFFERENT_IMAGE"
                    alert_level = "YELLOW"
                elif verdict == "DIFFERENT_PRESENTATION" and not discrepancy_type:
                    discrepancy_type = "NAME_DISCREPANCY"
                    alert_level = "BLUE"




        match_item = {
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
            "image_comparison": img_cmp
        }
        if ai_result:
            match_item["ai_verification"] = ai_result

        if not discrepancy_type:
            return ("MATCH", sp_name, match_item)

        discrepancy_item = dict(match_item)
        discrepancy_item.update({
            "description_comparison": compare_descriptions(off_prod.get("description", ""), best_sp_prod.get("description", "")),
            "discrepancy_type": discrepancy_type,
            "alert_level": alert_level
        })
        return ("DISCREPANCY", sp_name, discrepancy_item)

    if evaluated_pairs:
        with ThreadPoolExecutor(max_workers=3 if ai_active else 12) as executor:
            processed_results = list(executor.map(_eval_pair_full, evaluated_pairs))
    else:
        processed_results = []

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_official_products": len(official_products),
        "supermarkets_analyzed": list(supermarket_catalogs.keys()),
        "ai_enabled": ai_active,
        "discrepancies": [],
        "matches_list": [],
        "matches_summary": summary
    }

    for status, sp_name, item in processed_results:
        if status == "MATCH" and item:
            summary[sp_name]["matches"] += 1
            report["matches_list"].append(item)
        elif status == "DISCREPANCY" and item:
            summary[sp_name]["discrepancies"] += 1
            report["discrepancies"].append(item)

    report["matches_summary"] = summary

    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Reporte inteligente generado en: {OUTPUT_REPORT_PATH}")
    logger.info(f"   Total discrepancias encontradas: {len(report['discrepancies'])}")
    logger.info(f"   Total coincidencias verificadas: {len(report['matches_list'])}")
    return report

if __name__ == "__main__":
    run_matching(compare_images_flag=True, min_match_threshold=90.0, use_ai_flag=True)
