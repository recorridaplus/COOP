import asyncio
from playwright.async_api import async_playwright
import json

async def test_tienda_search_input():
    url = "https://www.tiendainglesa.com.uy/"
    print(f"Navegando a {url} para buscar via input de busqueda...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Encontrar input de búsqueda de GeneXus
        search_selector = "input[id*='SEARCH'], input[placeholder*='Buscar'], input[type='text']"
        await page.fill(search_selector, "conaprole")
        await page.press(search_selector, "Enter")
        print("Búsqueda enviada con 'Enter'. Esperando resultados...")
        await asyncio.sleep(5)

        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)

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

                const imgs = Array.from((link.querySelector("img") ? [link.querySelector("img")] : (parentCard ? parentCard.querySelectorAll("img") : [])));
                let prodImg = "";
                for (const imgEl of imgs) {
                    const src = imgEl.src || imgEl.getAttribute("data-src") || imgEl.getAttribute("data-original") || "";
                    if (src.includes("/images/small/") || src.includes("/images/large/") || src.includes("/images/medium/") || src.includes("prod-resize")) {
                        prodImg = src;
                        break;
                    }
                }

                if (text && text.length > 2 && href && !results.some(r => r.href === href)) {
                    results.push({
                        name: text.replace(/\\n/g, ' '),
                        image_url: prodImg,
                        href: href
                    });
                }
            });
            return results;
        }''')

        print(f"Total productos reales encontrados en Tienda Inglesa: {len(prods)}")
        for p in prods[:15]:
            print(" -", p["name"], "| Img:", p["image_url"])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tienda_search_input())
