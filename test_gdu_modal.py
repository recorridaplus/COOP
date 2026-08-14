import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando https://www.disco.com.uy/buscar?text=conaprole...")
        await page.goto("https://www.disco.com.uy/buscar?text=conaprole", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Imprimir modales o botones detectados
        modals = await page.query_selector_all(".modal, .dialog, [class*='sucursal'], [class*='pickup'], [class*='delivery']")
        print(f"Modales detectados: {len(modals)}")
        
        # Buscar botones de cerrar o seleccionar sucursal por defecto
        buttons = await page.query_selector_all("button")
        print(f"Botones detectados: {len(buttons)}")
        for b in buttons[:8]:
            txt = await b.inner_text()
            print(f"  Boton: '{txt.strip()}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
