import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

OUT_DIR = Path("data/supermarkets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

GDU_STORES = [
    {"key": "disco", "name": "Disco", "url": "https://www.disco.com.uy/"},
    {"key": "devoto", "name": "Devoto", "url": "https://www.devoto.com.uy/"},
    {"key": "geant", "name": "Géant", "url": "https://www.geant.com.uy/"},
]

async def scrape_gdu_store(page, store):
    print(f"\n==================== {store['name']} ====================")
    try:
        await page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Buscar el campo de búsqueda e interactuar
        search_input = await page.query_selector("input[type='search'], input[type='text'], input[placeholder*='Buscar'], .search-input")
        if not search_input:
            print("  ⚠️ No se encontró input de búsqueda en el home, probando navegacion a /buscar")
            await page.goto(f"{store['url']}buscar?text=conaprole", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
        else:
            print("  Escribiendo 'conaprole' en la barra de búsqueda...")
            await search_input.fill("conaprole")
            await search_input.press("Enter")
            await asyncio.sleep(4)

        # Scroll para cargar productos
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)

        products = await page.evaluate('''() => {
            const results = [];
            // Buscar tarjetas de producto Blazor
            const cards = document.querySelectorAll(".product-item, .card, [class*='product-card'], [class*='product_'], .rz-g-col, article");
            cards.forEach(card => {
                const nameEl = card.querySelector("h1, h2, h3, h4, .product-title, .title, .name, span.name");
                const imgEl = card.querySelector("img");
                const linkEl = card.querySelector("a");
                const name = nameEl ? nameEl.innerText.trim() : "";
                const href = linkEl ? linkEl.getAttribute("href") : "";
                const img = imgEl ? (imgEl.src || imgEl.getAttribute("data-src") || "") : "";

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

        print(f"  Resultados extraídos en {store['name']}: {len(products)}")
        if products:
            for p in products[:3]:
                print(f"    - {p['name']} | Img: {p['image_url'][:50]}")

        out_path = OUT_DIR / f"{store['key']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "supermarket": store["name"],
                "scraped_at": "2026-08-14T18:50:00Z",
                "total_products": len(products),
                "products": products
            }, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"  Error en {store['name']}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")
        page = await context.new_page()

        for store in GDU_STORES:
            await scrape_gdu_store(page, store)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
