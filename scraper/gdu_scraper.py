"""
gdu_scraper.py — Scraper para supermercados de Grupo Disco Uruguay (Disco, Devoto, Géant).

Utiliza Playwright para interactuar con la aplicación Blazor (.NET) Ecom.Gdu.Web,
escribir en la barra de búsqueda y extraer exclusivamente los productos de Conaprole.
"""

import json
import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper.base_scraper import BaseSupermarketScraper, SupermarketProduct

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "supermarkets"

CONFIGS = {
    "disco": {
        "name": "Disco",
        "url": "https://www.disco.com.uy/",
    },
    "devoto": {
        "name": "Devoto",
        "url": "https://www.devoto.com.uy/",
    },
    "geant": {
        "name": "Géant",
        "url": "https://www.geant.com.uy/",
    }
}

class GduScraper(BaseSupermarketScraper):
    def __init__(self, key: str):
        config = CONFIGS[key]
        super().__init__(config["name"], config["url"])
        self.key = key
        self.config = config

    async def async_search(self, query: str = "conaprole") -> list[SupermarketProduct]:
        logger.info(f"🔎 [{self.supermarket_name}] Abriendo sitio: {self.base_url}")
        results: list[SupermarketProduct] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Buscar input de búsqueda
                search_input = await page.query_selector("input[type='search'], input[type='text'], input[placeholder*='Buscar'], .search-input")
                if search_input:
                    logger.info(f"  Escribiendo '{query}' en la barra de búsqueda...")
                    await search_input.fill(query)
                    await search_input.press("Enter")
                    await asyncio.sleep(5)
                else:
                    await page.goto(f"{self.base_url}buscar?text={query}", wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(4)

                # Scroll gradual
                for _ in range(4):
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(1)

                raw_prods = await page.evaluate('''() => {
                    const results = [];
                    const cards = document.querySelectorAll(".product-item, .card, [class*='product-card'], [class*='product_'], .rz-g-col, article");
                    cards.forEach(card => {
                        const nameEl = card.querySelector("h1, h2, h3, h4, .product-title, .title, .name, span.name");
                        const imgEl = card.querySelector("img");
                        const linkEl = card.querySelector("a");
                        const name = nameEl ? nameEl.innerText.trim() : "";
                        const href = linkEl ? linkEl.getAttribute("href") : "";
                        const img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";

                        // Filtrar estrictamente productos que tengan relación con Conaprole o lácteos
                        const isConaprole = name.toLowerCase().includes("conaprole") || 
                                            name.toLowerCase().includes("colet") || 
                                            name.toLowerCase().includes("viva") || 
                                            name.toLowerCase().includes("deleite");

                        if (name && isConaprole && !results.some(r => r.name === name)) {
                            results.push({
                                name: name,
                                image_url: img,
                                description: "",
                                product_url: href ? (href.startsWith("http") ? href : window.location.origin + href) : window.location.href,
                                supermarket: window.location.host
                            });
                        }
                    });
                    return results;
                }''')

                now_str = datetime.now(timezone.utc).isoformat()
                for p in raw_prods:
                    results.append({
                        "name": p["name"],
                        "image_url": p["image_url"],
                        "description": "",
                        "product_url": p["product_url"],
                        "supermarket": self.supermarket_name,
                        "scraped_at": now_str
                    })

                logger.info(f"✅ [{self.supermarket_name}] Extraídos {len(results)} productos válidos de Conaprole.")
            except Exception as e:
                logger.error(f"❌ [{self.supermarket_name}] Error en scraping: {e}")
            finally:
                await browser.close()

        return results

    def search_product(self, query: str = "conaprole") -> list[SupermarketProduct]:
        return asyncio.run(self.async_search(query))

def scrape_and_save_gdu(query: str = "conaprole"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for key in CONFIGS.keys():
        scraper = GduScraper(key)
        products = scraper.search_product(query)
        out_file = DATA_DIR / f"{key}.json"
        data = {
            "supermarket": scraper.supermarket_name,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_products": len(products),
            "products": products
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Guardado {out_file}")

if __name__ == "__main__":
    scrape_and_save_gdu("conaprole")
