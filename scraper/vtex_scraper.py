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

def fetch_vtex_api_products(store_account: str, store_name: str, query: str = "conaprole") -> list[SupermarketProduct]:
    url = f"https://{store_account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={query}&_from=0&_to=49"
    logger.info(f"🔎 [{store_name}] Consultando API VTEX: {url}")
    results: list[SupermarketProduct] = []

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        now_str = datetime.now(timezone.utc).isoformat()

        for prod in data:
            name = prod.get("productName", "")
            description = prod.get("description", "") or prod.get("MetaTagDescription", "")
            link = prod.get("link", "")

            image_url = ""
            items = prod.get("items", [])
            if items and items[0].get("images"):
                image_url = items[0]["images"][0].get("imageUrl", "")

            results.append({
                "name": name,
                "image_url": image_url,
                "description": description,
                "product_url": link,
                "supermarket": store_name,
                "scraped_at": now_str
            })

        logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos.")
    except Exception as e:
        logger.error(f"❌ [{store_name}] Error scraping VTEX API: {e}")

    return results

async def scrape_tienda_inglesa(query: str = "conaprole") -> list[SupermarketProduct]:
    store_name = "Tienda Inglesa"
    url = "https://www.tiendainglesa.com.uy/"
    logger.info(f"🔎 [{store_name}] Scrapeando interactivamente en: {url}")
    results: list[SupermarketProduct] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=HEADERS["User-Agent"])

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(3)

            search_selector = "input[id*='SEARCH'], input[placeholder*='Buscar'], input[type='text']"
            await page.fill(search_selector, query)
            await page.press(search_selector, "Enter")

            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(4)

            for _ in range(4):
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

            logger.info(f"✅ [{store_name}] Extraídos {len(results)} productos reales con imágenes de catálogo.")
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

    # 3. Tienda Inglesa vía Playwright interactivo
    tienda_prods = asyncio.run(scrape_tienda_inglesa(query))
    with open(DATA_DIR / "tiendainglesa.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "Tienda Inglesa", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tienda_prods), "products": tienda_prods}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_vtex_scrapers("conaprole")
