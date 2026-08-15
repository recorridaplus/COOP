"""
vtex_scraper.py — Scraper para supermercados basados en VTEX y Tienda Inglesa
con paginación completa y soporte para todas las submarcas oficiales de Conaprole.
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

DEFAULT_QUERIES = [
    "conaprole", "colet", "viva", "deleite", "polar food", "blancanube", 
    "conamigos", "biotop", "alpazul", "magretto", "sinfonia", "maxima", 
    "triffle", "alpa", "lactolate", "conacrem", "conahorro", "baccanal"
]

def fetch_vtex_api_products(store_account: str, store_name: str, queries: list[str] | str = None) -> list[SupermarketProduct]:
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    results: list[SupermarketProduct] = []
    seen_urls: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    for q in queries:
        page_size = 50
        page_idx = 0
        while page_idx < 5:  # Paginación hasta 250 productos por término
            from_idx = page_idx * page_size
            to_idx = from_idx + page_size - 1
            url = f"https://{store_account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={q}&_from={from_idx}&_to={to_idx}"
            logger.info(f"🔎 [{store_name}] Consultando API VTEX (query '{q}' pág {page_idx+1}): {url}")

            try:
                resp = httpx.get(url, headers=HEADERS, timeout=15)
                if resp.status_code in [404, 204]:
                    break
                data = resp.json()
                if not data or not isinstance(data, list):
                    break

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

                if len(data) < page_size:
                    break
                page_idx += 1

            except Exception as e:
                logger.error(f"❌ [{store_name}] Error en query '{q}' pág {page_idx+1}: {e}")
                break

    logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos únicos.")
    return results

async def scrape_tienda_inglesa(queries: list[str] | str = None) -> list[SupermarketProduct]:
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    store_name = "Tienda Inglesa"
    logger.info(f"🔎 [{store_name}] Scrapeando interactivamente para {len(queries)} submarcas...")
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
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"  ⚠️ Timeout cargando {url}, procesando contenido parcial...")

                # Scroll más profundo para cargar la góndola completa
                for _ in range(6):
                    await page.evaluate("window.scrollBy(0, 1200)")
                    await asyncio.sleep(0.8)

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

    eldorado_prods = fetch_vtex_api_products("eldoradouy", "El Dorado", queries)
    with open(DATA_DIR / "eldorado.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "El Dorado", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(eldorado_prods), "products": eldorado_prods}, f, ensure_ascii=False, indent=2)

    tata_prods = fetch_vtex_api_products("tatauy", "TATA", queries)
    with open(DATA_DIR / "tata.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "TATA", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tata_prods), "products": tata_prods}, f, ensure_ascii=False, indent=2)

    tienda_prods = asyncio.run(scrape_tienda_inglesa(queries))
    with open(DATA_DIR / "tiendainglesa.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "Tienda Inglesa", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tienda_prods), "products": tienda_prods}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_vtex_scrapers()
