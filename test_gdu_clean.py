import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

OUT_DIR = Path("data/supermarkets")

STORES = [
    {"key": "disco", "name": "Disco", "url": "https://www.disco.com.uy/"},
    {"key": "devoto", "name": "Devoto", "url": "https://www.devoto.com.uy/"},
    {"key": "geant", "name": "Géant", "url": "https://www.geant.com.uy/"},
]

async def scrape_gdu(store):
    print(f"\n==================== {store['name']} ====================")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            await page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Buscar input e interactuar
            inp = await page.query_selector("input[type='search'], input[type='text'], input[placeholder*='Buscar']")
            if inp:
                print("  Escribiendo 'conaprole'...")
                await inp.fill("conaprole")
                await inp.press("Enter")
                await asyncio.sleep(5)

            # Scroll
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)

            prods = await page.evaluate('''() => {
                const results = [];
                // Selector amplio de elementos
                const elements = document.querySelectorAll("a, div, article");
                elements.forEach(el => {
                    const txt = el.innerText ? el.innerText.trim() : "";
                    const imgEl = el.querySelector("img");
                    const href = el.getAttribute("href") || (el.querySelector("a") ? el.querySelector("a").getAttribute("href") : "");
                    
                    // Si el texto del elemento tiene 1-3 líneas y contiene "conaprole" o "colet"
                    if (txt && txt.length < 150 && txt.length > 5 && imgEl && (txt.toLowerCase().includes("conaprole") || txt.toLowerCase().includes("colet"))) {
                        const firstLine = txt.split("\\n")[0].trim();
                        const img = imgEl.src || imgEl.getAttribute("data-src") || "";
                        if (firstLine && !results.some(r => r.name === firstLine)) {
                            results.push({
                                name: firstLine,
                                image_url: img,
                                description: "",
                                product_url: href ? (href.startsWith("http") ? href : window.location.origin + href) : window.location.href,
                                supermarket: window.location.host
                            });
                        }
                    }
                });
                return results;
            }''')

            print(f"  Resultados extraídos en {store['name']}: {len(prods)}")
            if prods:
                for p in prods[:3]:
                    print(f"    - {p['name']} | Img: {p['image_url'][:50]}")

            out_file = OUT_DIR / f"{store['key']}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump({
                    "supermarket": store["name"],
                    "scraped_at": "2026-08-14T18:52:00Z",
                    "total_products": len(prods),
                    "products": prods
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"  Error en {store['name']}: {e}")
        finally:
            await browser.close()

async def main():
    for store in STORES:
        await scrape_gdu(store)

if __name__ == "__main__":
    asyncio.run(main())
