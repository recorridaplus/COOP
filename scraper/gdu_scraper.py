"""
gdu_scraper.py — Scraper para supermercados de Grupo Disco Uruguay (Disco, Devoto, Géant).

Utiliza Playwright para interactuar con la aplicación Blazor (.NET) Ecom.Gdu.Web,
escribir en la barra de búsqueda y extraer productos de Conaprole y sus submarcas.
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

DEFAULT_QUERIES = [
    "conaprole", "colet", "viva", "deleite", "polar food", "blancanube", 
    "conamigos", "biotop", "alpazul", "magretto", "sinfonia", "maxima", 
    "triffle", "alpa", "lactolate", "conacrem", "conahorro", "baccanal"
]

class GduScraper(BaseSupermarketScraper):
    def __init__(self, key: str):
        config = CONFIGS[key]
        super().__init__(config["name"], config["url"])
        self.key = key
        self.config = config

    async def async_search(self, queries: list[str] | str = None) -> list[SupermarketProduct]:
        if queries is None:
            queries = DEFAULT_QUERIES
        elif isinstance(queries, str):
            queries = [queries]

        logger.info(f"🔎 [{self.supermarket_name}] Abriendo sitio: {self.base_url} (Submarcas: {len(queries)})")
        results: list[SupermarketProduct] = []
        seen_urls: set[str] = set()
        now_str = datetime.now(timezone.utc).isoformat()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                for q in queries:
                    target_url = f"{self.base_url}buscar?text={q}"
                    logger.info(f"  [{self.supermarket_name}] NAVEGANDO A: {target_url}")
                    try:
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                        await asyncio.sleep(3)
                    except Exception:
                        pass

                    # Scroll gradual para cargar la grilla completa
                    for _ in range(5):
                        await page.evaluate("window.scrollBy(0, 900)")
                        await asyncio.sleep(0.8)

                    raw_prods = await page.evaluate('''() => {
                        const results = [];
                        const cards = document.querySelectorAll(".product-item, .card, [class*='product-card'], [class*='product_'], .rz-g-col, article");
                        const keywords = [
                            "conaprole", "colet", "viva", "deleite", "polar", "blancanube", "sinfonia", 
                            "sinfonía", "conamigos", "baccanal", "conahorro", "lacto", "maxima", "máxima", 
                            "triffle", "biotop", "alpazul", "magretto", "alpa"
                        ];

                        cards.forEach(card => {
                            const nameEl = card.querySelector("h1, h2, h3, h4, .product-title, .title, .name, span.name");
                            const imgEl = card.querySelector("img");
                            const linkEl = card.querySelector("a");
                            const name = nameEl ? nameEl.innerText.trim() : "";
                            const href = linkEl ? linkEl.getAttribute("href") : "";
                            const img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";

                            const nameLow = name.toLowerCase();
                            const isConaprole = keywords.some(kw => nameLow.includes(kw));

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

                    for p_item in raw_prods:
                        url_p = p_item["product_url"]
                        if p_item["name"] and url_p not in seen_urls:
                            seen_urls.add(url_p)
                            results.append({
                                "name": p_item["name"],
                                "image_url": p_item["image_url"],
                                "description": "",
                                "product_url": url_p,
                                "supermarket": self.supermarket_name,
                                "scraped_at": now_str
                            })

                logger.info(f"✅ [{self.supermarket_name}] Extraídos {len(results)} productos válidos de Conaprole y submarcas.")
            except Exception as e:
                logger.error(f"❌ [{self.supermarket_name}] Error en scraping: {e}")
            finally:
                await browser.close()

        return results

    def search_product(self, queries: list[str] | str = None) -> list[SupermarketProduct]:
        return asyncio.run(self.async_search(queries))

def scrape_and_save_gdu(queries: list[str] | str = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for key in CONFIGS.keys():
        scraper = GduScraper(key)
        products = scraper.search_product(queries)
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
    scrape_and_save_gdu()
