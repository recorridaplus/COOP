import asyncio
from playwright.async_api import async_playwright
import json

async def test_tienda_specific_queries():
    terms = ["leche", "queso", "yogur", "colet", "dulce de leche", "manteca"]
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        for term in terms:
            url = f"https://www.tiendainglesa.com.uy/busqueda?ft={term}"
            print(f"Scrapeando Tienda Inglesa termino: {term} ({url})...")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                items = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll("a[href*='.producto']"));
                    return links.map(link => {
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
                        return { name: text.replace(/\\n/g, ' '), image_url: prodImg, href: href };
                    }).filter(x => x.name.length > 2);
                }''')

                print(f"  Encontrados: {len(items)}")
                for item in items:
                    if not any(r["href"] == item["href"] for r in results):
                        results.append(item)
            except Exception as e:
                print(f"  Error en {term}: {e}")

        print(f"\nTotal productos consolidados de Tienda Inglesa: {len(results)}")
        for r in results[:15]:
            print(" -", r["name"], "| Img:", r["image_url"][:60])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tienda_specific_queries())
