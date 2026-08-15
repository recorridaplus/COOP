"""
conaprole_scraper.py — Extrae el catálogo oficial de productos de conaprole.uy
incluyendo el gramaje/presentación exacto (ej. 40g, 80g, 200g, 500g, 970g, 1L).
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.conaprole.uy"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "conaprole_catalog.json"

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
}

def extract_grammage_from_text_or_slug(text: str, slug: str) -> str:
    """Extrae el gramaje/volumen del texto de la tarjeta o del slug URL."""
    match_text = re.search(r'\b(\d+(?:[.,]\d+)?\s*(?:g|gr|grs|gramos|kg|kilo|kilos|ml|cc|l|lt|litro|litros))\b', text, re.IGNORECASE)
    if match_text:
        return match_text.group(1).strip()

    match_slug = re.search(r'[-_](\d+(?:[.,]\d+)?\s*(?:g|gr|grs|kg|ml|cc|l))\b', slug, re.IGNORECASE)
    if match_slug:
        return match_slug.group(1).replace('-', ' ').strip()

    return ""

def fetch_category_product_items(client: httpx.Client, category_slug: str) -> list[dict]:
    items = []
    page = 1

    while True:
        cat_url = f"{BASE_URL}/categoria-producto/{category_slug}/"
        if page > 1:
            cat_url += f"page/{page}/"

        logger.info(f"  Categoría '{category_slug}' — página {page}: {cat_url}")
        try:
            resp = client.get(cat_url, timeout=15)
            if resp.status_code == 404:
                break
        except Exception:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        product_links = soup.select("a[href*='/producto/']")
        if not product_links:
            break

        seen_on_page = set()
        for a in product_links:
            href = a.get("href")
            if not href or href in seen_on_page:
                continue
            seen_on_page.add(href)

            full_text = a.get_text(strip=True, separator=" ")
            slug = href.rstrip("/").split("/")[-1]
            gram = extract_grammage_from_text_or_slug(full_text, slug)

            items.append({
                "url": href,
                "slug": slug,
                "card_text": full_text,
                "grammage": gram
            })

        next_btn = soup.select_one("a.next, a[rel='next'], .pagination .next a")
        if not next_btn:
            break
        page += 1

    return items

def parse_product_page(client: httpx.Client, item_meta: dict, category: str) -> dict | None:
    url = item_meta["url"]
    gram = item_meta.get("grammage", "")

    try:
        resp = client.get(url, timeout=12)
        if resp.status_code != 200:
            return None
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    article = soup.select_one("article.content_information")
    if not article:
        return None

    h1 = article.select_one("h1")
    if not h1:
        return None
    
    base_name = h1.get_text(strip=True)

    has_gram_in_name = bool(re.search(r'\b\d+\s*(?:g|gr|grs|kg|ml|cc|l|lt)\b', base_name, re.IGNORECASE))
    if gram and not has_gram_in_name:
        final_name = f"{base_name} {gram}"
    else:
        final_name = base_name

    images = []
    img_tag = article.select_one("img")
    if img_tag:
        src = img_tag.get("src") or img_tag.get("data-src") or ""
        if src and "cdn.conaprole.uy" in src:
            images.append(src)

    description = ""
    desc_section = soup.select_one("section.content_description")
    if desc_section:
        headings_div = desc_section.select_one(".headings")
        if headings_div:
            p = headings_div.select_one("p")
            if p:
                description = p.get_text(strip=True)

    slug = item_meta["slug"]

    return {
        "id": slug,
        "name": final_name,
        "description": description or "",
        "category": category,
        "url": url,
        "images": images,
    }

def scrape_conaprole() -> list[dict]:
    all_products = []
    seen_urls: set[str] = set()

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for slug, category_name in CATEGORIES.items():
            logger.info(f"\n📂 Categoría: {category_name}")
            items = fetch_category_product_items(client, slug)

            if not items:
                continue

            unique_items = []
            for item in items:
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    unique_items.append(item)

            logger.info(f"  Procesando {len(unique_items)} presentaciones en paralelo...")

            def _worker(item):
                return parse_product_page(client, item, category_name)

            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(_worker, unique_items))

            for r in results:
                if r:
                    all_products.append(r)

    return all_products

def main():
    logger.info("🐄 Iniciando scraper oficial Conaprole en paralelo con extracción de Gramaje...")
    products = scrape_conaprole()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_products": len(products),
        "products": products,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Catálogo oficial guardado con gramajes completos en: {OUTPUT_PATH}")
    logger.info(f"   Total productos extraídos: {len(products)}")

if __name__ == "__main__":
    main()
