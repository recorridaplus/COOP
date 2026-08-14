import asyncio
from playwright.async_api import async_playwright

async def debug_tienda_inglesa_selectors():
    url = "https://www.tiendainglesa.com.uy/busqueda?ft=conaprole"
    print(f"Navegando a {url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36")

        await page.goto(url, wait_until="networkidle", timeout=40000)
        await asyncio.sleep(4)

        # Scroll to load all products
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(1)

        info = await page.evaluate('''() => {
            const allImages = Array.from(document.querySelectorAll("img")).map(i => ({
                src: i.src,
                data_src: i.getAttribute("data-src"),
                alt: i.alt,
                parentClass: i.parentElement ? i.parentElement.className : ""
            }));
            
            const allLinks = Array.from(document.querySelectorAll("a")).map(a => ({
                href: a.getAttribute("href") || "",
                text: a.innerText ? a.innerText.trim() : "",
                html: a.innerHTML.substring(0, 150)
            })).filter(l => l.href.includes("busqueda") || l.href.includes("producto") || l.href.includes(".html") || l.href.includes("/"));

            return {
                img_count: allImages.length,
                sample_imgs: allImages.slice(0, 15),
                link_count: allLinks.length,
                sample_links: allLinks.slice(0, 15)
            };
        }''')

        print("Total imágenes:", info["img_count"])
        print("Muestra imágenes:")
        for img in info["sample_imgs"]:
            print("  src:", img["src"])
            print("  d-src:", img["data_src"])
            print("  alt:", img["alt"])
            print("  parent:", img["parentClass"])
            print("-" * 40)

        print("\nTotal links:", info["link_count"])
        print("Muestra links:")
        for link in info["sample_links"][:10]:
            print("  href:", link["href"])
            print("  text:", link["text"][:40])
            print("-" * 40)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_tienda_inglesa_selectors())
