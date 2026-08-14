import asyncio
from playwright.async_api import async_playwright
import json

async def capture_tienda_inglesa():
    url = "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    print(f"Navegando a {url}...")
    
    api_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        async def on_response(response):
            if "api" in response.url or "graphql" in response.url or "search" in response.url or "busqueda" in response.url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        data = await response.json()
                        api_responses.append({"url": response.url, "data": data})
                except Exception:
                    pass

        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=40000)
        await asyncio.sleep(5)

        print(f"Capturadas {len(api_responses)} respuestas JSON de red:")
        for r in api_responses:
            print("  URL:", r["url"][:120])
            txt = json.dumps(r["data"])[:200]
            print("  Data:", txt)
            print("-" * 50)

        # Inspect DOM images and links
        dom_cards = await page.evaluate('''() => {
            const items = [];
            document.querySelectorAll("a, div").forEach(el => {
                const img = el.querySelector("img");
                const text = el.innerText ? el.innerText.trim() : "";
                if (img && text.toLowerCase().includes("conaprole")) {
                    items.push({
                        text: text.substring(0, 50),
                        src: img.src,
                        data_src: img.getAttribute("data-src"),
                        srcset: img.getAttribute("srcset")
                    });
                }
            });
            return items;
        }''')

        print(f"\nItems encontrados en el DOM: {len(dom_cards)}")
        for item in dom_cards[:5]:
            print("  DOM Item:", item)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_tienda_inglesa())
