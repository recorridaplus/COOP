import json
from collections import Counter

with open('data/conaprole_catalog.json', encoding='utf-8') as f:
    cat = json.load(f)

print(f'Total: {cat["total_products"]} productos')
print(f'Scrapeado: {cat["scraped_at"]}')
print()

by_cat = Counter(p['category'] for p in cat['products'])
for cat_name, count in sorted(by_cat.items()):
    print(f'  {cat_name}: {count}')

print()
for p in cat['products'][:2]:
    print('--- PRODUCTO EJEMPLO ---')
    print(f'  Nombre: {p["name"]}')
    print(f'  Categoria: {p["category"]}')
    desc = p["description"][:100] + '...' if p["description"] else '(vacia)'
    print(f'  Descripcion: {desc}')
    print(f'  Imagenes: {len(p["images"])}')
    img = p["images"][0] if p["images"] else '(ninguna)'
    print(f'  Primera imagen: {img}')
    print(f'  URL: {p["url"]}')
    print()

sin_img = [p for p in cat['products'] if not p['images']]
print(f'Sin imagenes: {len(sin_img)}')
sin_desc = [p for p in cat['products'] if not p['description']]
print(f'Sin descripcion: {len(sin_desc)}')
