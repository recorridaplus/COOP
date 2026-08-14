import json
from pathlib import Path

DATA_DIR = Path("data")
TIENDA_FILE = DATA_DIR / "supermarkets" / "tienda_inglesa.json"

if not TIENDA_FILE.exists():
    print(f"No existe {TIENDA_FILE}")
else:
    with open(TIENDA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    
    prods = data.get("products", [])
    print(f"Total productos scrapeados de Tienda Inglesa: {len(prods)}")
    print("Muestra de productos:")
    for p in prods[:10]:
        print("  - Nombre   :", p.get("name"))
        print("    Imagen   :", p.get("image_url"))
        print("    Producto :", p.get("product_url"))
        print()
