import json
import sys
from pathlib import Path
from PIL import Image
import imagehash

sys.path.insert(0, str(Path(__file__).parent.parent))
from comparator.image_comparator import fetch_image, trim_background, compare_images

# Cargar catálogo Conaprole y Devoto
with open("data/conaprole_catalog.json", encoding="utf-8") as f:
    cat = json.load(f)

with open("data/supermarkets/devoto.json", encoding="utf-8") as f:
    dev = json.load(f)

# Buscar "Yogur Con Fondo de Durazno"
off_item = next(p for p in cat["products"] if "fondo de durazno" in p["name"].lower())
dev_item = next(p for p in dev["products"] if "fondo durazno" in p["name"].lower())

url_off = off_item["images"][0]
url_dev = dev_item["image_url"]

print("URL Oficial:", url_off)
print("URL Devoto :", url_dev)
print()

img_off = fetch_image(url_off)
img_dev = fetch_image(url_dev)

print("Tamaño Oficial original:", img_off.size)
print("Tamaño Devoto original :", img_dev.size)

# pHash directo sin trim
hash_off_raw = imagehash.phash(img_off)
hash_dev_raw = imagehash.phash(img_dev)
dist_raw = hash_off_raw - hash_dev_raw
print(f"pHash distancia SIN trim: {dist_raw}")

# Trim
trimmed_off = trim_background(img_off)
trimmed_dev = trim_background(img_dev)

print("Tamaño Oficial tras trim:", trimmed_off.size)
print("Tamaño Devoto tras trim :", trimmed_dev.size)

hash_off_trim = imagehash.phash(trimmed_off)
hash_dev_trim = imagehash.phash(trimmed_dev)
dist_trim = hash_off_trim - hash_dev_trim
print(f"pHash distancia CON trim: {dist_trim}")

# Probar dHash y aHash también
print("dHash distancia con trim:", imagehash.dhash(trimmed_off) - imagehash.dhash(trimmed_dev))
print("aHash distancia con trim:", imagehash.average_hash(trimmed_off) - imagehash.average_hash(trimmed_dev))
