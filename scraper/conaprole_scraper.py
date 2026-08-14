"""
conaprole_scraper.py — Extrae el catálogo oficial de productos de conaprole.uy

Genera data/conaprole_catalog.json con la estructura:
{
  "scraped_at": "2024-...",
  "products": [
    {
      "id": "leche-entera-1l",
      "name": "Leche Entera",
      "description": "...",
      "category": "Leches",
      "url": "https://www.conaprole.uy/producto/leche-entera/",
      "images": ["https://...jpg"]
    },
    ...
  ]
}

Uso:
    python scraper/conaprole_scraper.py
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from tqdm import tqdm

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper.rate_limiter import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.conaprole.uy"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "conaprole_catalog.json"

# Categorías del sitio (slug → nombre legible)
# Verificadas contra el nav real del sitio
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


def fetch_category_product_urls(
    client: httpx.Client, limiter: RateLimiter, category_slug: str
) -> list[str]:
    """Obtiene todas las URLs de productos dentro de una categoría."""
    urls = []
    page = 1

    while True:
        cat_url = f"{BASE_URL}/categoria-producto/{category_slug}/"
        if page > 1:
            cat_url += f"page/{page}/"

        logger.info(f"  Categoría '{category_slug}' — página {page}: {cat_url}")
        resp = limiter.get(client, cat_url)

        if resp is None or resp.status_code == 404:
            break

        soup = BeautifulSoup(resp.text, "lxml")

        # Los productos están en enlaces con clase que contiene 'product'
        product_links = soup.select("a.datalink[data-link='product']")
        if not product_links:
            # Intentar selector alternativo: href que contenga /producto/
            product_links = soup.select("a[href*='/producto/']")

        if not product_links:
            logger.debug(f"  No se encontraron productos en página {page}, fin de categoría.")
            break

        page_urls = list({a["href"] for a in product_links if a.get("href")})
        urls.extend(page_urls)
        logger.info(f"  → {len(page_urls)} productos encontrados en página {page}")

        # Verificar si hay página siguiente
        next_btn = soup.select_one("a.next, a[rel='next'], .pagination .next a")
        if not next_btn:
            break
        page += 1

    return urls


def parse_product_page(
    client: httpx.Client, limiter: RateLimiter, url: str, category: str
) -> dict | None:
    """
    Extrae los datos de una página de producto individual.

    Estructura real del sitio (verificada por inspección de HTML):
    - article.content_information → contiene h1 (nombre) + img (imagen del producto)
    - section.content_description .headings p → ingredientes (usado como descripción)
    - section.content_products → productos relacionados (NO tocar)
    """
    resp = limiter.get(client, url)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # El contenedor del producto es article.content_information
    article = soup.select_one("article.content_information")
    if not article:
        logger.warning(f"  ⚠️  No se encontró article.content_information en: {url}")
        return None

    # --- Nombre (h1 dentro del artículo del producto) ---
    h1 = article.select_one("h1")
    if not h1:
        logger.warning(f"  ⚠️  No se encontró h1 en: {url}")
        return None
    name = h1.get_text(strip=True)

    # --- Imagen (única img dentro del artículo del producto) ---
    images = []
    img_tag = article.select_one("img")
    if img_tag:
        src = img_tag.get("src") or img_tag.get("data-src") or ""
        if src and "cdn.conaprole.uy" in src:
            images.append(src)

    # --- Descripción (ingredientes del producto, si existen) ---
    # El sitio no tiene descripción libre; la info textual más útil son los ingredientes
    description = ""
    desc_section = soup.select_one("section.content_description")
    if desc_section:
        headings_div = desc_section.select_one(".headings")
        if headings_div:
            p = headings_div.select_one("p")
            if p:
                description = p.get_text(strip=True)

    # --- Slug / ID ---
    slug = url.rstrip("/").split("/")[-1]

    product = {
        "id": slug,
        "name": name,
        "description": description or "",
        "category": category,
        "url": url,
        "images": images,
    }

    logger.debug(f"  ✓ {name} ({len(images)} imagen/es)")
    return product


def scrape_conaprole() -> list[dict]:
    """Función principal: recorre todas las categorías y extrae todos los productos."""
    limiter = RateLimiter(BASE_URL, delay_min=2.0, delay_max=5.0)
    all_products = []
    seen_urls: set[str] = set()

    with httpx.Client(follow_redirects=True) as client:
        for slug, category_name in CATEGORIES.items():
            logger.info(f"\n📂 Categoría: {category_name}")
            product_urls = fetch_category_product_urls(client, limiter, slug)

            if not product_urls:
                logger.info(f"  (Sin productos encontrados)")
                continue

            logger.info(f"  Total URLs: {len(product_urls)}")

            for url in tqdm(product_urls, desc=f"  {category_name}", unit="prod"):
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                product = parse_product_page(client, limiter, url, category_name)
                if product:
                    all_products.append(product)

    return all_products


def main():
    logger.info("🐄 Iniciando scraper de catálogo Conaprole...")
    logger.info(f"   Categorías a procesar: {', '.join(CATEGORIES.keys())}")

    products = scrape_conaprole()

    # Guardar resultado
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_products": len(products),
        "products": products,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Catálogo guardado: {OUTPUT_PATH}")
    logger.info(f"   Total productos: {len(products)}")


if __name__ == "__main__":
    main()
