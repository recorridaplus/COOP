"""
vtex_scraper.py — Scraper para supermercados basados en VTEX y Tienda Inglesa.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import TypedDict
import httpx
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "supermarkets"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

class SupermarketProduct(TypedDict):
    name: str
    image_url: str
    description: str
    product_url: str
    supermarket: str
    scraped_at: str

DEFAULT_QUERIES = ["conaprole", "colet", "viva", "deleite", "polar food", "blancanube", "conamigos"]

def fetch_vtex_api_products(store_account: str, store_name: str, queries: list[str] | str = None) -> list[SupermarketProduct]:
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    results: list[SupermarketProduct] = []
    seen_urls: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    for q in queries:
        url = f"https://{store_account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={q}&_from=0&_to=49"
        logger.info(f"🔎 [{store_name}] Consultando API VTEX (query '{q}'): {url}")

        try:
            resp = httpx.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for prod in data:
                name = prod.get("productName", "")
                description = prod.get("description", "") or prod.get("MetaTagDescription", "")
                link = prod.get("link", "")

                if not link or link in seen_urls:
                    continue

                image_url = ""
                items = prod.get("items", [])
                if items and items[0].get("images"):
                    image_url = items[0]["images"][0].get("imageUrl", "")

                seen_urls.add(link)
                results.append({
                    "name": name,
                    "image_url": image_url,
                    "description": description,
                    "product_url": link,
                    "supermarket": store_name,
                    "scraped_at": now_str
                })

        except Exception as e:
            logger.error(f"❌ [{store_name}] Error en query '{q}': {e}")

    logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos únicos.")
    return results

async def scrape_tienda_inglesa(queries: list[str] | str = None) -> list[SupermarketProduct]:
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    store_name = "Tienda Inglesa"
    logger.info(f"🔎 [{store_name}] Scrapeando interactivamente para queries: {queries}")
    results: list[SupermarketProduct] = []
    seen_urls: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=HEADERS["User-Agent"])

        try:
            for q in queries:
                url = f"https://www.tiendainglesa.com.uy/busqueda?0,{q}"
                logger.info(f"  Scrapeando query '{q}' en {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(3)

                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)

                raw_prods = await page.evaluate('''() => {
                    const results = [];
                    const links = Array.from(document.querySelectorAll("a[href*='.producto']"));

                    links.forEach(link => {
                        const href = link.getAttribute("href") || "";
                        const text = link.innerText ? link.innerText.trim() : "";

                        let parentCard = link.parentElement;
                        let steps = 0;
                        while (parentCard && !parentCard.querySelector("img") && steps < 5) {
                            parentCard = parentCard.parentElement;
                            steps++;
                        }

                        const imgs = Array.from((link.querySelector("img") ? [link.querySelector("img")] : (parentCard ? parentCard.querySelectorAll("img") : [])));
                        let prodImg = "";

                        for (const imgEl of imgs) {
                            const src = imgEl.src || imgEl.getAttribute("data-src") || imgEl.getAttribute("data-original") || "";
                            const isStamp = src.includes("/Ico/") || src.includes("ico_") || src.includes("banner") || src.includes("logo");
                            if (src && !isStamp && (src.includes("/images/") || src.includes("prod-resize") || src.includes(".jpg"))) {
                                prodImg = src;
                                break;
                            }
                        }

                        if (!prodImg) {
                            for (const imgEl of imgs) {
                                const src = imgEl.src || imgEl.getAttribute("data-src") || "";
                                if (src && !src.includes("ico_search") && !src.includes("main_logo")) {
                                    prodImg = src;
                                    break;
                                }
                            }
                        }

                        if (text && text.length > 2 && href && !results.some(r => r.product_url.includes(href))) {
                            const fullHref = href.startsWith("http") ? href : "https://www.tiendainglesa.com.uy" + href;
                            results.push({
                                name: text.replace(/\\n/g, ' '),
                                image_url: prodImg,
                                description: "",
                                product_url: fullHref
                            });
                        }
                    });
                    return results;
                }''')

                for p_item in raw_prods:
                    url_p = p_item["product_url"]
                    if p_item["name"] and len(p_item["name"]) > 2 and url_p not in seen_urls:
                        seen_urls.add(url_p)
                        results.append({
                            "name": p_item["name"],
                            "image_url": p_item["image_url"],
                            "description": "",
                            "product_url": url_p,
                            "supermarket": store_name,
                            "scraped_at": now_str
                        })

            logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos reales de catálogo.")
        except Exception as e:
            logger.error(f"❌ [{store_name}] Error en scraping: {e}")
        finally:
            await browser.close()

    return results

def run_vtex_scrapers(queries: list[str] | str = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. El Dorado vía API
    eldorado_prods = fetch_vtex_api_products("eldoradouy", "El Dorado", queries)
    with open(DATA_DIR / "eldorado.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "El Dorado", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(eldorado_prods), "products": eldorado_prods}, f, ensure_ascii=False, indent=2)

    # 2. TATA vía API
    tata_prods = fetch_vtex_api_products("tatauy", "TATA", queries)
    with open(DATA_DIR / "tata.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "TATA", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tata_prods), "products": tata_prods}, f, ensure_ascii=False, indent=2)

    # 3. Tienda Inglesa vía Playwright interactivo
    tienda_prods = asyncio.run(scrape_tienda_inglesa(queries))
    with open(DATA_DIR / "tiendainglesa.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "Tienda Inglesa", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tienda_prods), "products": tienda_prods}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_vtex_scrapers()
