import asyncio
from playwright.async_api import async_playwright

async def test_tienda_queries():
    queries = [
        "https://www.tiendainglesa.com.uy/busqueda?1,0,,conaprole,0",
        "https://www.tiendainglesa.com.uy/busqueda?conaprole",
        "https://www.tiendainglesa.com.uy/supermercado/busqueda?0=conaprole",
        "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        for url in queries:
            print(f"Probando URL: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)

                prods = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll("a[href*='.producto']"));
                    return links.map(l => l.innerText ? l.innerText.trim() : "").filter(t => t.length > 2);
                }''')

                conaprole_found = [p for p in prods if "conaprole" in p.lower()]
                print(f"  Total productos encontrados: {len(prods)}")
                print(f"  Productos con 'Conaprole': {len(conaprole_found)}")
                if conaprole_found:
                    print("  Ejemplos:", conaprole_found[:3])
            except Exception as e:
                print("  Error:", e)
            print("-" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tienda_queries())
