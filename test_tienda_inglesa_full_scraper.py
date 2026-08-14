import asyncio
from playwright.async_api import async_playwright
import json

async def scrape_tienda_inglesa_real():
    url = "https://www.tiendainglesa.com.uy/"
    print(f"Buscando 'conaprole' interactivamente en Tienda Inglesa...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await asyncio.sleep(3)

        search_selector = "input[id*='SEARCH'], input[placeholder*='Buscar'], input[type='text']"
        await page.fill(search_selector, "conaprole")
        await page.press(search_selector, "Enter")

        # Esperar la navegación provocada por la búsqueda
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(4)

        for _ in range(4):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(1)

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
                    const isStamp = src.includes("/Ico/") || src.includes("ico_") || src.includes("banner") || src.includes("logo");
                    if (src && !isStamp && (src.includes("/images/") || src.includes("prod-resize") || src.includes(".jpg"))) {
                        prodImg = src;
                        break;
                    }
                }
                
                if (!prodImg) {
                    for (const imgEl of imgs) {
                        const src = imgEl.src || imgEl.getAttribute("data-src") || "";
                        if (src && !src.includes("ico_search") && !src.includes("main_logo")) {
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

        print(f"\nExtraídos {len(raw_prods)} productos reales de Tienda Inglesa:")
        for p in raw_prods[:15]:
            print(" -", p["name"])
            print("   Img :", p["image_url"])
            print("   Url :", p["product_url"])
            print("-" * 50)

        await browser.close()
        return raw_prods

if __name__ == "__main__":
    asyncio.run(scrape_tienda_inglesa_real())
