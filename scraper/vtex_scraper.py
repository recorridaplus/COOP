"""
vtex_scraper.py — Scraper para supermercados VTEX (El Dorado), VTEX FastStore (TATA)
y Tienda Inglesa con extracción de Conaprole y todas sus submarcas oficiales.
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
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
    "conaprole", "colet", "viva", "deleite", "polar", "blancanube", 
    "conamigos", "biotop", "alpazul", "magretto", "sinfonia", "maxima", 
    "triffle", "alpa", "lactolate", "conacrem", "conahorro", "baccanal"
]

def fetch_eldorado_products(queries: list[str] | str = None) -> list[SupermarketProduct]:
    """Extrae productos de El Dorado utilizando la API de catálogo VTEX."""
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    store_name = "El Dorado"
    store_account = "eldoradouy"
    results: list[SupermarketProduct] = []
    seen_urls: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    logger.info(f"[INFO] [{store_name}] Consultando catalogo VTEX ({len(queries)} consultas)...")
    for q in queries:
        page_size = 50
        page_idx = 0
        while page_idx < 5:
            from_idx = page_idx * page_size
            to_idx = from_idx + page_size - 1
            url = f"https://{store_account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={q}&_from={from_idx}&_to={to_idx}"

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
                logger.error(f"[ERROR] [{store_name}] Error en query '{q}' pag {page_idx+1}: {e}")
                break

    logger.info(f"[OK] [{store_name}] Extraidos {len(results)} productos unicos.")
    return results

def fetch_tata_products(queries: list[str] | str = None) -> list[SupermarketProduct]:
    """Extrae productos de TATA utilizando su API GraphQL FastStore."""
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    store_name = "TATA"
    graphql_url = "https://www.tata.com.uy/api/graphql?operationName=ProductsQuery"
    results: list[SupermarketProduct] = []
    seen_ids: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    logger.info(f"[INFO] [{store_name}] Consultando FastStore GraphQL...")

    # 1. Búsqueda por marca 'conaprole'
    after = "0"
    while True:
        variables = {
            "first": 50,
            "after": after,
            "sort": "score_desc",
            "term": "",
            "selectedFacets": [
                {"key": "brand", "value": "conaprole"},
                {"key": "channel", "value": "{\"salesChannel\":\"4\",\"regionId\":\"\"}"},
                {"key": "locale", "value": "es-uy"}
            ]
        }
        try:
            r = httpx.get(f"{graphql_url}&variables={json.dumps(variables)}", headers=HEADERS, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
            if not edges:
                break

            for edge in edges:
                node = edge.get("node", {})
                pid = node.get("id") or node.get("productId") or node.get("slug")
                if not pid or pid in seen_ids:
                    continue

                name = node.get("name", "")
                slug = node.get("slug", "")
                images = node.get("image", [])
                img_url = images[0].get("url") if images else ""
                prod_url = f"https://www.tata.com.uy/{slug}/p" if slug else "https://www.tata.com.uy/"

                seen_ids.add(pid)
                results.append({
                    "name": name,
                    "image_url": img_url,
                    "description": "",
                    "product_url": prod_url,
                    "supermarket": store_name,
                    "scraped_at": now_str
                })

            if len(edges) < 50:
                break
            after = str(int(after) + 50)
        except Exception as e:
            logger.error(f"[ERROR] [{store_name}] Error en brand conaprole: {e}")
            break

    # 2. Búsqueda por términos y submarcas
    for term in queries:
        after = "0"
        while True:
            variables = {
                "first": 50,
                "after": after,
                "sort": "score_desc",
                "term": term,
                "selectedFacets": [
                    {"key": "channel", "value": "{\"salesChannel\":\"4\",\"regionId\":\"\"}"},
                    {"key": "locale", "value": "es-uy"}
                ]
            }
            try:
                r = httpx.get(f"{graphql_url}&variables={json.dumps(variables)}", headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    break
                data = r.json()
                edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                if not edges:
                    break

                for edge in edges:
                    node = edge.get("node", {})
                    pid = node.get("id") or node.get("productId") or node.get("slug")
                    name = node.get("name", "")
                    brand_info = node.get("brand", {})
                    brand_name = brand_info.get("name", "").lower() if isinstance(brand_info, dict) else ""

                    name_low = name.lower()
                    if not (term.lower() in name_low or "conaprole" in name_low or "conaprole" in brand_name):
                        continue

                    if not pid or pid in seen_ids:
                        continue

                    slug = node.get("slug", "")
                    images = node.get("image", [])
                    img_url = images[0].get("url") if images else ""
                    prod_url = f"https://www.tata.com.uy/{slug}/p" if slug else "https://www.tata.com.uy/"

                    seen_ids.add(pid)
                    results.append({
                        "name": name,
                        "image_url": img_url,
                        "description": "",
                        "product_url": prod_url,
                        "supermarket": store_name,
                        "scraped_at": now_str
                    })

                if len(edges) < 50:
                    break
                after = str(int(after) + 50)
            except Exception as e:
                break

    logger.info(f"[OK] [{store_name}] Extraidos {len(results)} productos unicos.")
    return results

async def scrape_tienda_inglesa(queries: list[str] | str = None) -> list[SupermarketProduct]:
    """Extrae productos de Tienda Inglesa con Playwright y URLs directas de búsqueda."""
    if queries is None:
        queries = DEFAULT_QUERIES
    elif isinstance(queries, str):
        queries = [queries]

    store_name = "Tienda Inglesa"
    logger.info(f"[INFO] [{store_name}] Scrapeando para {len(queries)} submarcas...")
    results: list[SupermarketProduct] = []
    seen_urls: set[str] = set()
    now_str = datetime.now(timezone.utc).isoformat()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()

        try:
            for q in queries:
                url = f"https://www.tiendainglesa.com.uy/supermercado/busqueda?0,0,{q},0"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"  [WARN] Timeout cargando {url}, procesando parcial...")

                # Scroll gradual
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 900)")
                    await asyncio.sleep(0.5)

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
                            if (!src) continue;
                            const isIcon = src.includes("/Ico/") || src.includes("ico_") || src.includes("banner") || src.includes("logo") || src.includes("badge") || src.includes("gluten");
                            if (!isIcon && (src.includes("/images/") || src.includes("prod-resize") || src.includes(".jpg") || src.includes(".png"))) {
                                prodImg = src;
                                break;
                            }
                        }

                        if (!prodImg) {
                            for (const imgEl of imgs) {
                                const src = imgEl.src || imgEl.getAttribute("data-src") || "";
                                if (src && !src.includes("ico_") && !src.includes("main_logo") && !src.includes("gluten")) {
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

            logger.info(f"[OK] [{store_name}] Extraidos {len(results)} productos reales.")
        except Exception as e:
            logger.error(f"[ERROR] [{store_name}] Error en scraping: {e}")
        finally:
            await browser.close()

    return results

def run_vtex_scrapers(queries: list[str] | str = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    eldorado_prods = fetch_eldorado_products(queries)
    with open(DATA_DIR / "eldorado.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "El Dorado", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(eldorado_prods), "products": eldorado_prods}, f, ensure_ascii=False, indent=2)

    tata_prods = fetch_tata_products(queries)
    with open(DATA_DIR / "tata.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "TATA", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tata_prods), "products": tata_prods}, f, ensure_ascii=False, indent=2)

    tienda_prods = asyncio.run(scrape_tienda_inglesa(queries))
    with open(DATA_DIR / "tiendainglesa.json", "w", encoding="utf-8") as f:
        json.dump({"supermarket": "Tienda Inglesa", "scraped_at": datetime.now(timezone.utc).isoformat(), "total_products": len(tienda_prods), "products": tienda_prods}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_vtex_scrapers()
