import httpx
from bs4 import BeautifulSoup
import re

url = "https://www.conaprole.uy/categoria-producto/quesos/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
}

resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
soup = BeautifulSoup(resp.text, "lxml")

# Buscar todos los contenedores de producto en la grilla de la categoría
product_cards = soup.select(".product, .product-item, div[class*='product'], a[href*='/producto/']")

print(f"Total links o tarjetas de producto encontrados en {url}: {len(product_cards)}")

seen_urls = set()
for card in product_cards:
    href = card.get("href") or (card.select_one("a[href*='/producto/']")["href"] if card.select_one("a[href*='/producto/']") else "")
    if not href or href in seen_urls:
        continue
    seen_urls.add(href)

    text = card.get_text(strip=True, separator=" ")
    img_el = card.select_one("img")
    alt = img_el.get("alt", "") if img_el else ""
    title = img_el.get("title", "") if img_el else ""
    
    # Buscar si hay un elemento específico para el título o gramaje
    h2 = card.select_one("h2, h3, h4, .title, .product-title")
    title_text = h2.get_text(strip=True) if h2 else ""

    # Extraer gramaje del slug si aparece (ej: -80g, -150g, -500g, -1kg, -250ml)
    slug = href.rstrip("/").split("/")[-1]
    match_gram = re.search(r'[-_](\d+\s*(?:g|gr|kg|ml|cc|l))\b', slug, re.IGNORECASE)
    slug_gram = match_gram.group(1) if match_gram else ""

    print(f"HREF : {href}")
    print(f"SLUG : {slug}")
    print(f"TITLE: {title_text}")
    print(f"TEXT : {text[:80]}")
    print(f"ALT  : {alt}")
    print(f"SLUG GRAM: {slug_gram}")
    print("-" * 50)
