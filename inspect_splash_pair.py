import json
import sys
from pathlib import Path
from PIL import Image
import imagehash

sys.path.insert(0, str(Path(__file__).parent.parent))
from comparator.image_comparator import fetch_image, trim_white_background, compare_images

with open("data/conaprole_catalog.json", encoding="utf-8") as f:
    cat = json.load(f)

# Buscar "Helado Palito D-Frutta Durazno/Kiwi"
off_item = next(p for p in cat["products"] if "durazno/kiwi" in p["name"].lower() or "durazno-kiwi" in p["name"].lower())

# Buscar en supermercados
sp_files = list(Path("data/supermarkets").glob("*.json"))
sp_item = None
sp_name = ""

for sp_file in sp_files:
    with open(sp_file, encoding="utf-8") as f:
        sp_data = json.load(f)
    for p in sp_data.get("products", []):
        if "durazno-kiwi" in p.get("name", "").lower() or "durazno/kiwi" in p.get("name", "").lower():
            sp_item = p
            sp_name = sp_data.get("supermarket", sp_file.stem)
            break
    if sp_item:
        break

url_off = off_item["images"][0]
url_sp = sp_item["image_url"]

print(f"Oficial: '{off_item['name']}' -> {url_off}")
print(f"Super  : '{sp_item['name']}' ({sp_name}) -> {url_sp}")

img_off = fetch_image(url_off)
img_sp = fetch_image(url_sp)

print("\nTamaño original Oficial:", img_off.size)
print("Tamaño original Super  :", img_sp.size)

trimmed_off = trim_white_background(img_off)
trimmed_sp = trim_white_background(img_sp)

print("\nTamaño tras Trim Oficial:", trimmed_off.size)
print("Tamaño tras Trim Super  :", trimmed_sp.size)

aspect_off = round(trimmed_off.width / trimmed_off.height, 3)
aspect_sp = round(trimmed_sp.width / trimmed_sp.height, 3)

print(f"Aspect ratio Oficial: {aspect_off} (Ancho {trimmed_off.width} / Alto {trimmed_off.height})")
print(f"Aspect ratio Super  : {aspect_sp} (Ancho {trimmed_sp.width} / Alto {trimmed_sp.height})")

res_off = trimmed_off.resize((256, 256), Image.Resampling.LANCZOS)
res_sp = trimmed_sp.resize((256, 256), Image.Resampling.LANCZOS)

h_off = imagehash.phash(res_off)
h_sp = imagehash.phash(res_sp)

dist = h_off - h_sp
print(f"\npHash distancia: {dist}")

result = compare_images(url_off, url_sp)
print("Resultado compare_images:", result)
