"""
gdu_scraper.py — Scraper para supermercados de Grupo Disco Uruguay (Disco, Devoto, Géant).

Interactúa con la aplicación Blazor (.NET) Ecom.Gdu.Web a través del buscador dinámico
del portal para extraer el catálogo completo de Conaprole y sus submarcas oficiales.
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
    "conaprole", "colet", "viva", "deleite", "polar", "blancanube", 
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

        logger.info(f"[INFO] [{self.supermarket_name}] Abriendo sitio: {self.base_url} ({len(queries)} consultas)")
        results: list[SupermarketProduct] = []
        seen_names: set[str] = set()
        now_str = datetime.now(timezone.utc).isoformat()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768}
            )
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=35000)
                await asyncio.sleep(2)

                for q in queries:
                    logger.info(f"  [{self.supermarket_name}] Buscando termino: '{q}'...")
                    search_input = await page.query_selector("input.input-buscador, input#InputSearch, input[placeholder*='Busca' i], input[type='search'], input[type='text']")
                    if not search_input:
                        await page.goto(self.base_url, wait_until="networkidle", timeout=25000)
                        search_input = await page.query_selector("input.input-buscador, input#InputSearch, input[placeholder*='Busca' i]")

                    if not search_input:
                        logger.warning(f"    [WARN] No se encontro input de busqueda en {self.supermarket_name}")
                        continue

                    try:
                        await search_input.click()
                        await search_input.fill("")
                        await search_input.fill(q)
                        await search_input.press("Enter")
                        await asyncio.sleep(4)

                        # Scroll para disparar el lazy load de Blazor
                        for _ in range(4):
                            await page.evaluate("window.scrollBy(0, 900)")
                            await asyncio.sleep(0.6)

                        raw_prods = await page.evaluate('''() => {
                            const list = [];
                            const cards = document.querySelectorAll(".prod-item-suggest-box, .product-item, .card, [class*='product_'], article, .rz-card, div");
                            const seenInRun = new Set();

                            cards.forEach(card => {
                                const txt = card.innerText || "";
                                if (!txt.includes("$") || txt.length > 300 || txt.length < 8) return;

                                const imgEl = card.querySelector("img");
                                const linkEl = card.querySelector("a");
                                const src = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";
                                const href = linkEl ? linkEl.getAttribute("href") : "";

                                if (!src || src.includes("icon") || src.includes("logo") || src.includes("svg") || src.includes("user")) return;

                                const lines = txt.split("\\n").map(s => s.trim()).filter(Boolean);
                                const title = lines.find(l => l.length > 4 && !l.startsWith("$") && l !== "Agregar" && !l.toLowerCase().includes("online") && !l.toLowerCase().includes("descuento")) || lines[0];

                                if (title && !seenInRun.has(title)) {
                                    seenInRun.add(title);
                                    list.push({
                                        name: title,
                                        image_url: src,
                                        product_url: href ? (href.startsWith("http") ? href : window.location.origin + href) : window.location.href
                                    });
                                }
                            });
                            return list;
                        }''')

                        count_new = 0
                        for p_item in raw_prods:
                            name_clean = p_item["name"].strip()
                            if name_clean and name_clean not in seen_names:
                                seen_names.add(name_clean)
                                results.append({
                                    "name": name_clean,
                                    "image_url": p_item["image_url"],
                                    "description": "",
                                    "product_url": p_item["product_url"],
                                    "supermarket": self.supermarket_name,
                                    "scraped_at": now_str
                                })
                                count_new += 1

                        logger.info(f"    -> {len(raw_prods)} items detectados ({count_new} nuevos). Acumulados: {len(results)}")
                    except Exception as e:
                        logger.warning(f"    [WARN] Error procesando termino '{q}': {e}")

                logger.info(f"[OK] [{self.supermarket_name}] Extraidos {len(results)} productos validos.")
            except Exception as e:
                logger.error(f"[ERROR] [{self.supermarket_name}] Error en scraping: {e}")
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
        logger.info(f"[OK] Guardado {out_file}")

if __name__ == "__main__":
    scrape_and_save_gdu()
