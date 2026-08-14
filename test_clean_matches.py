import json

with open("data/latest_comparison_report.json", encoding="utf-8") as f:
    rep = json.load(f)

print("Total discrepancias en reporte actual:", len(rep["discrepancies"]))

img_matches = [d for d in rep["discrepancies"] if d.get("image_comparison") and d["image_comparison"].get("status") == "MATCH"]
print(f"Discrepancias donde la IMAGEN ES COINCIDENTE (MATCH): {len(img_matches)}")

for d in img_matches[:5]:
    print("  Oficial:", d["conaprole_product"]["name"])
    print("  Super  :", d["supermarket_product"]["name"])
    print("  Score  :", d["name_comparison"]["similarity_score"])
    print("  Image  :", d["image_comparison"]["details"])
    print("-" * 50)
