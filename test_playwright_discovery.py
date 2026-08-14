import asyncio
from playwright.async_api import async_playwright
import json

async def test_search(url, store_name):
    print(f"\n==================== {store_name.upper()} ({url}) ====================")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Interceptar respuestas JSON de API
        json_responses = []

        def handle_response(response):
            if "json" in response.headers.get("content-type", "") or "api" in response.url:
                if "product" in response.url.lower() or "search" in response.url.lower() or "busca" in response.url.lower():
                    json_responses.append(response.url)

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
        except Exception as e:
            print(f"  Timeout/Error al cargar: {e}")

        title = await page.title()
        print(f"  Título de página: {title}")

        # Capturar elementos de producto
        images = await page.eval_on_selector_all(
            "img", "imgs => imgs.map(i => i.src).filter(s => s && s.includes('http'))"
        )
        print(f"  Imágenes encontradas: {len(images)}")
        if images:
            print(f"  Ejemplo imagen: {images[0]}")

        if json_responses:
            print(f"  APIs JSON detectadas en segundo plano ({len(json_responses)}):")
            for api_url in json_responses[:5]:
                print(f"    - {api_url}")

        await browser.close()

async def main():
    await test_search("https://www.tiendainglesa.com.uy/busqueda?ft=conaprole", "Tienda Inglesa")
    await test_search("https://www.tata.com.uy/conaprole?_q=conaprole&map=ft", "TATA")
    await test_search("https://www.disco.com.uy/conaprole", "Disco")
    await test_search("https://www.eldorado.com.uy/conaprole?_q=conaprole&map=ft", "El Dorado")

if __name__ == "__main__":
    asyncio.run(main())
