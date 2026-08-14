import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_tienda_inglesa_genexus():
    url = "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    print(f"Navegando a {url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        await page.goto(url, wait_until="networkidle", timeout=40000)
        await asyncio.sleep(4)

        prods = await page.evaluate('''() => {
            const results = [];
            // GeneXus grid items or links
            const cards = document.querySelectorAll(".SectionGridProduct, .ProductBlock, a[href*='.producto'], div[id*='GRID']");
            cards.forEach(card => {
                const nameEl = card.querySelector(".product-title, .title, .ProductName, span, h2, h3") || card;
                const imgEl = card.querySelector("img");
                const name = nameEl.innerText ? nameEl.innerText.trim() : "";
                const href = card.getAttribute("href") || "";
                
                let img = "";
                if (imgEl) {
                    img = imgEl.src || imgEl.getAttribute("data-src") || imgEl.getAttribute("data-original") || "";
                }

                if (name && name.toLowerCase().includes("conaprole")) {
                    results.push({
                        name: name.replace(/\\n/g, ' '),
                        image_url: img,
                        href: href,
                        img_html: imgEl ? imgEl.outerHTML : ""
                    });
                }
            });
            return results;
        }''')

        print(f"Productos extraídos de Tienda Inglesa: {len(prods)}")
        for p in prods[:8]:
            print(f"  Nombre: {p['name'][:40]}")
            print(f"  Image : {p['image_url']}")
            print(f"  HTML  : {p['img_html'][:150]}")
            print("-" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_tienda_inglesa_genexus())
