import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

OUT_DIR = Path("data/supermarkets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STORES = [
    {
        "key": "tiendainglesa",
        "name": "Tienda Inglesa",
        "url": "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole",
        "card_selector": "a[href*='.producto']",
    },
    {
        "key": "tata",
        "name": "TATA",
        "url": "https://www.tata.com.uy/conaprole?_q=conaprole&map=ft",
        "card_selector": ".vtex-product-summary-2-x-container, article, a[href*='/p']",
    },
    {
        "key": "eldorado",
        "name": "El Dorado",
        "url": "https://www.eldorado.com.uy/conaprole?_q=conaprole&map=ft",
        "card_selector": ".vtex-product-summary-2-x-container, article, a[href*='/p']",
    },
    {
        "key": "disco",
        "name": "Disco",
        "url": "https://www.disco.com.uy/conaprole",
        "card_selector": ".product-item, .card, [class*='product']",
    },
    {
        "key": "devoto",
        "name": "Devoto",
        "url": "https://www.devoto.com.uy/conaprole",
        "card_selector": ".product-item, .card, [class*='product']",
    },
    {
        "key": "geant",
        "name": "Géant",
        "url": "https://www.geant.com.uy/conaprole",
        "card_selector": ".product-item, .card, [class*='product']",
    }
]

async def scrape_store(page, store):
    print(f"\n==================== {store['name']} ====================")
    try:
        await page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Scroll 3 veces para activar lazy-loading
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)

        products = await page.evaluate('''() => {
            const results = [];
            const cards = document.querySelectorAll("a[href*='.producto'], a[href*='/p'], .vtex-product-summary-2-x-container, .product-item");
            
            cards.forEach(card => {
                let nameEl = card.querySelector("h1, h2, h3, .product-title, .title, .vtex-product-summary-2-x-productBrand, span");
                let imgEl = card.querySelector("img");
                let href = card.getAttribute("href") || (card.querySelector("a") ? card.querySelector("a").getAttribute("href") : "");
                
                let name = nameEl ? nameEl.innerText.trim() : "";
                let img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";

                if (name && name.length > 3 && !results.some(r => r.name === name)) {
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

        print(f"  Productos encontrados: {len(products)}")
        if products:
            print("  Ejemplos:")
            for p in products[:3]:
                print(f"    - {p['name']} | Img: {p['image_url'][:50]}")

        out_path = OUT_DIR / f"{store['key']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "supermarket": store["name"],
                "scraped_at": "2026-08-14T18:00:00Z",
                "total_products": len(products),
                "products": products
            }, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"  Error scraping {store['name']}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")
        page = await context.new_page()

        for store in STORES:
            await scrape_store(page, store)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
