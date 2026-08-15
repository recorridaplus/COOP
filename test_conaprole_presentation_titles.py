import httpx
from bs4 import BeautifulSoup
import re
import json

CATEGORIES = {
    "leches": "Leches",
    "yogures": "Yogures",
    "quesos": "Quesos",
    "dulce-de-leche": "Dulce de leche",
    "postres": "Postres",
    "congelados": "Congelados",
    "helados": "Helados",
    "jugos": "Jugos",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
}

def extract_products_from_category(cat_slug: str):
    url = f"https://www.conaprole.uy/categoria-producto/{cat_slug}/"
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")

    # Los links de productos en la grilla
    links = soup.select("a[href*='/producto/']")
    prods = []
    seen = set()

    for a in links:
        href = a.get("href", "")
        if not href or href in seen:
            continue
        seen.add(href)

        # Buscar el texto del título en el contenedor o elementos internos
        full_text = a.get_text(strip=True, separator=" ")
        
        # Buscar h2/h3 o spans de título dentro del a o su padre
        title_el = a.select_one("h2, h3, h4, .title, .product-title")
        raw_title = title_el.get_text(strip=True) if title_el else full_text

        # Extraer el nombre del producto + la presentación/gramaje si aparece
        # En Conaprole, la primera parte de full_text suele ser "Nombre Gramaje Descripcion"
        # Ej: "Queso Ricotta 500g Queso no madurado..."
        slug = href.rstrip("/").split("/")[-1]
        
        # Intentar matchear patrón de gramaje (ej: 80g, 150g, 500g, 1kg, 250ml, 1l)
        gram_match = re.search(r'\b(\d+(?:[.,]\d+)?\s*(?:g|gr|kg|kilo|ml|cc|l|lt|litro))\b', full_text, re.IGNORECASE)
        gram = gram_match.group(1) if gram_match else ""

        # Si el slug tiene gramaje y el texto no lo tenía
        if not gram:
            slug_match = re.search(r'[-_](\d+(?:[.,]\d+)?\s*(?:g|gr|kg|ml|cc|l))\b', slug, re.IGNORECASE)
            if slug_match:
                gram = slug_match.group(1)

        prods.append({
            "href": href,
            "slug": slug,
            "raw_text": full_text[:60],
            "extracted_gram": gram
        })

    return prods

all_extracted = {}
for cat in CATEGORIES:
    items = extract_products_from_category(cat)
    all_extracted[cat] = len(items)
    print(f"Categoría '{cat}': {len(items)} productos con gramaje extraído")
    for item in items[:4]:
        print("  - Slug :", item["slug"])
        print("    Texto:", item["raw_text"])
        print("    Gram :", item["extracted_gram"])
        print()
