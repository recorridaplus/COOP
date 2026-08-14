"""
gdu_scraper.py — Scraper para supermercados de Grupo Disco Uruguay (Disco, Devoto, Géant).

Todos comparten la plataforma Blazor (.NET) Ecom.Gdu.Web.
"""

import json
import logging
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scraper.base_scraper import BaseSupermarketScraper, SupermarketProduct

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "supermarkets"

CONFIGS = {
    "disco": {
        "name": "Disco",
        "search_url_template": "https://www.disco.com.uy/conaprole",
    },
    "devoto": {
        "name": "Devoto",
        "search_url_template": "https://www.devoto.com.uy/conaprole",
    },
    "geant": {
        "name": "Géant",
        "search_url_template": "https://www.geant.com.uy/conaprole",
    }
}

class GduScraper(BaseSupermarketScraper):
    def __init__(self, key: str):
        config = CONFIGS[key]
        super().__init__(config["name"], config["search_url_template"])
        self.key = key
        self.config = config

    async def async_search(self, query: str = "conaprole") -> list[SupermarketProduct]:
        url = self.config["search_url_template"].format(query=query)
        logger.info(f"🔎 [{self.supermarket_name}] Buscando en: {url}")

        results: list[SupermarketProduct] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=25000)
                await asyncio.sleep(3) # Esperar a Blazor Server WebSocket/rendering

                raw_prods = await page.evaluate('''() => {
                    const results = [];
                    const cards = document.querySelectorAll(".product-item, .card, [class*='product-card'], [class*='product']");
                    cards.forEach(card => {
                        const nameEl = card.querySelector(".product-title, .title, h3, h2, span.name");
                        const imgEl = card.querySelector("img");
                        const linkEl = card.querySelector("a");
                        const name = nameEl ? nameEl.innerText.trim() : "";
                        const href = linkEl ? linkEl.getAttribute("href") : "";
                        const img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src")) : "";
                        
                        if (name && name.toLowerCase().includes("conaprole") && img) {
                            results.push({
                                name: name,
                                image_url: img,
                                description: "",
                                product_url: href ? (href.startsWith("http") ? href : window.location.origin + href) : window.location.href
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
                        "description": p["description"],
                        "product_url": p["product_url"],
                        "supermarket": self.supermarket_name,
                        "scraped_at": now_str
                    })

                logger.info(f"✅ [{self.supermarket_name}] Extraídos {len(results)} productos.")
            except Exception as e:
                logger.error(f"❌ [{self.supermarket_name}] Error en scraping: {e}")
            finally:
                await browser.close()

        return results

    def search_product(self, query: str = "conaprole") -> list[SupermarketProduct]:
        return asyncio.run(self.async_search(query))

def scrape_and_save_gdu(key: str, query: str = "conaprole"):
    scraper = GduScraper(key)
    products = scraper.search_product(query)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
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
    return products

if __name__ == "__main__":
    for k in CONFIGS.keys():
        scrape_and_save_gdu(k, "conaprole")
