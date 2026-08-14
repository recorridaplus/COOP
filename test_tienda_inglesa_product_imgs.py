import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_tienda_inglesa_product_imgs():
    url = "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    print(f"Navegando a {url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        await page.goto(url, wait_until="networkidle", timeout=40000)
        await asyncio.sleep(4)

        prods = await page.evaluate('''() => {
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
                
                let imgEl = link.querySelector("img") || (parentCard ? parentCard.querySelector("img") : null);
                let imgSrc = "";
                if (imgEl) {
                    imgSrc = imgEl.src || imgEl.getAttribute("data-src") || imgEl.getAttribute("data-original") || "";
                }

                if (text && text.length > 2 && !results.some(r => r.href === href)) {
                    results.push({
                        name: text.replace(/\\n/g, ' '),
                        href: href,
                        image_url: imgSrc
                    });
                }
            });
            return results;
        }''')

        print(f"Productos extraídos de Tienda Inglesa con imágenes: {len(prods)}")
        for p in prods[:10]:
            print(f"  Nombre: {p['name'][:50]}")
            print(f"  Image : {p['image_url']}")
            print(f"  Href  : {p['href']}")
            print("-" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_tienda_inglesa_product_imgs())
