import sys
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent.parent))

from comparator.matcher import load_json, DATA_DIR, REPORT_OUTPUT_PATH, CONAPROLE_PATH, SUPERMARKETS_DIR, calculate_match_score
from comparator.image_comparator import compare_images

print("Testing matcher with min_match_threshold=90.0 and active parallel image comparison...")

def run_matching_fast_images(min_match_threshold: float = 90.0) -> dict:
    conaprole_data = load_json(CONAPROLE_PATH)
    official_products = conaprole_data.get("products", [])

    supermarket_files = list(SUPERMARKETS_DIR.glob("*.json"))
    supermarket_catalogs = {}
    for sp_file in supermarket_files:
        sp_data = load_json(sp_file)
        if sp_data and sp_data.get("products"):
            sp_name = sp_data.get("supermarket", sp_file.stem)
            supermarket_catalogs[sp_name] = sp_data.get("products", [])

    candidate_pairs = []

    for sp_name, sp_products in supermarket_catalogs.items():
        if not sp_products:
            continue

        for off_prod in official_products:
            off_name = off_prod["name"]
            off_cat = off_prod.get("category", "")
            off_img = off_prod["images"][0] if off_prod.get("images") else ""

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

    print(f"Pares candidatos con similitud >= {min_match_threshold}%: {len(candidate_pairs)}")

    # Función helper para comparar imagen individual en ThreadPool
    def evaluate_pair(pair):
        sp_name, off_prod, best_sp_prod, score = pair
        off_img = off_prod["images"][0] if off_prod.get("images") else ""
        sp_img = best_sp_prod.get("image_url", "")
        
        img_cmp = None
        if off_img and sp_img:
            img_cmp = compare_images(off_img, sp_img)
            
        return (sp_name, off_prod, best_sp_prod, score, img_cmp)

    print("Descargando y evaluando imágenes en paralelo (15 workers)...")
    with ThreadPoolExecutor(max_workers=15) as executor:
        evaluated_pairs = list(executor.map(evaluate_pair, candidate_pairs))

    report = {
        "generated_at": conaprole_data.get("scraped_at", ""),
        "total_official_products": len(official_products),
        "supermarkets_analyzed": list(supermarket_catalogs.keys()),
        "discrepancies": [],
        "matches_summary": {}
    }

    summary = {sp: {"matches": 0, "discrepancies": 0} for sp in supermarket_catalogs.keys()}

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
        elif score < 95.0: # Si no son fotos distintas pero el nombre tiene ligera variación
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
                "image_comparison": img_cmp,
                "discrepancy_type": discrepancy_type,
                "alert_level": alert_level
            })
        else:
            summary[sp_name]["matches"] += 1

    report["matches_summary"] = summary

    from collections import Counter
    types = Counter(d.get("discrepancy_type") for d in report["discrepancies"])
    print("\nDesglose real de discrepancias:")
    for t, count in types.items():
        print(f"  {t}: {count}")

    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReporte guardado en {REPORT_OUTPUT_PATH}")
    return report

if __name__ == "__main__":
    run_matching_fast_images(90.0)
