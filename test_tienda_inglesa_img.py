import asyncio
from playwright.async_api import async_playwright

async def inspect_tienda_inglesa():
    url = "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    print(f"Navegando a {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        prods = await page.evaluate('''() => {
            const list = [];
            document.querySelectorAll(".product-item, .vtex-product-summary-2-x-container, a[href*='.producto'], div.card").forEach(el => {
                const imgEl = el.querySelector("img");
                const titleEl = el.querySelector(".product-title, .title, span, h2, h3");
                if (imgEl && titleEl) {
                    list.push({
                        title: titleEl.innerText.trim(),
                        src: imgEl.src,
                        data_src: imgEl.getAttribute("data-src"),
                        data_original: imgEl.getAttribute("data-original"),
                        srcset: imgEl.getAttribute("srcset"),
                        outer: imgEl.outerHTML.substring(0, 200)
                    });
                }
            });
            return list;
        }''')

        print(f"Productos encontrados: {len(prods)}")
        for p in prods[:10]:
            print("  Título:", p["title"])
            print("  src   :", p["src"])
            print("  d-src :", p["data_src"])
            print("  html  :", p["outer"])
            print("-" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_tienda_inglesa())
