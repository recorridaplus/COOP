"""
vtex_scraper.py — Scraper para supermercados VTEX (El Dorado, TATA, Tienda Inglesa).
"""

import json
import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
import httpx
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper.base_scraper import BaseSupermarketScraper, SupermarketProduct

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "supermarkets"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

VTEX_ACCOUNTS = {
    "eldorado": {
        "name": "El Dorado",
        "account": "eldoradouy"
    },
    "tata": {
        "name": "TATA",
        "account": "tatauy"
    }
}

def fetch_vtex_api_products(account: str, store_name: str, query: str = "conaprole") -> list[SupermarketProduct]:
    """
    Extrae productos directamente usando la API Catalog System de VTEX.
    """
    logger.info(f"⚡ [{store_name}] Consultando API VTEX para '{query}'...")
    products: list[SupermarketProduct] = []
    _from = 0
    step = 50
    now_str = datetime.now(timezone.utc).isoformat()

    while True:
        url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={query}&_from={_from}&_to={_from + step - 1}"
        try:
            r = httpx.get(url, headers=HEADERS, timeout=12)
            if r.status_code not in [200, 206]:
                logger.debug(f"Fin o status {r.status_code}")
                break
            batch = r.json()
            if not batch:
                break

            for p in batch:
                name = p.get("productName", "").strip()
                link = p.get("link", "")
                items = p.get("items", [])
                img = ""
                if items and items[0].get("images"):
                    img = items[0]["images"][0].get("imageUrl", "")

                if name:
                    products.append({
                        "name": name,
                        "image_url": img,
                        "description": p.get("description", "") or "",
                        "product_url": link,
                        "supermarket": store_name,
                        "scraped_at": now_str
                    })

            if len(batch) < step:
                break
            _from += step
        except Exception as e:
            logger.error(f"Error en API VTEX ({account}): {e}")
            break

    logger.info(f"✅ [{store_name}] Extraídos {len(products)} productos vía API VTEX.")
    return products

async def fetch_tienda_inglesa_playwright(query: str = "conaprole") -> list[SupermarketProduct]:
    """
    Extrae productos de Tienda Inglesa renderizando con Playwright.
    """
    store_name = "Tienda Inglesa"
    url = f"https://www.tiendainglesa.com.uy/busqueda?ft={query}"
    logger.info(f"🔎 [{store_name}] Buscando en: {url}")
    results: list[SupermarketProduct] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=HEADERS["User-Agent"])

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)

            raw_prods = await page.evaluate('''() => {
                const results = [];
                const cards = document.querySelectorAll("a[href*='.producto']");
                cards.forEach(card => {
                    const nameEl = card.querySelector(".product-title, .title, span, h2, h3") || card;
                    const imgEl = card.querySelector("img");
                    const name = nameEl.innerText ? nameEl.innerText.trim() : "";
                    const href = card.getAttribute("href") || "";
                    const img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";

                    if (name && href && !results.some(r => r.product_url === href)) {
                        results.push({
                            name: name,
                            image_url: img,
                            description: "",
                            product_url: href.startsWith("http") ? href : "https://www.tiendainglesa.com.uy" + href
                        });
                    }
                });
                return results;
            }''')

            now_str = datetime.now(timezone.utc).isoformat()
            for p in raw_prods:
                if p["name"] and len(p["name"]) > 2:
                    results.append({
                        "name": p["name"],
                        "image_url": p["image_url"],
                        "description": "",
                        "product_url": p["product_url"],
                        "supermarket": store_name,
                        "scraped_at": now_str
                    })

            logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos.")
        except Exception as e:
            logger.error(f"❌ [{store_name}] Error en scraping: {e}")
        finally:
            await browser.close()

    return results

def run_vtex_scrapers(query: str = "conaprole"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. El Dorado vía API
    eldorado_prods = fetch_vtex_api_products("eldoradouy", "El Dorado", query)
    with open(DATA_DIR / "eldorado.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "El Dorado", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(eldorado_prods), "products": eldorado_prods}, f, ensure_ascii=False, indent=2)

    # 2. TATA vía API
    tata_prods = fetch_vtex_api_products("tatauy", "TATA", query)
    with open(DATA_DIR / "tata.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "TATA", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tata_prods), "products": tata_prods}, f, ensure_ascii=False, indent=2)

    # 3. Tienda Inglesa vía Playwright
    ti_prods = asyncio.run(fetch_tienda_inglesa_playwright(query))
    with open(DATA_DIR / "tiendainglesa.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "Tienda Inglesa", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(ti_prods), "products": ti_prods}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_vtex_scrapers("conaprole")
