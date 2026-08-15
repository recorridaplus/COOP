import httpx
from bs4 import BeautifulSoup
import json

urls = [
    "https://www.conaprole.uy/producto/queso-rallado/",
    "https://www.conaprole.uy/producto/dulce-de-leche-clasico/",
    "https://www.conaprole.uy/categoria-producto/quesos/"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
}

for url in urls:
    print(f"==================================================")
    print(f"Inspeccionando URL: {url}")
    print(f"==================================================")
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")

    # Imprimir h1, h2, h3, spans, divs con clases interesantes
    print("H1:", soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else "No H1")
    
    # Buscar elementos de presentaciones, variantes, thumbnails, o list-items
    items = soup.select(".content_information, .presentations, .variants, .presentation, ul.slides, .gallery, [data-title], [title]")
    print(f"Elementos encontrados con posibles presentaciones: {len(items)}")

    for el in soup.find_all(True):
        # Buscar atributos title, alt, data-title, data-name, etc.
        attrs = el.attrs
        for k, v in attrs.items():
            if any(term in str(v).lower() for term in ["80g", "150g", "500g", "80 g", "gramos", "1kg", "ml", "cc", "presentacion"]):
                print(f"  Tag <{el.name}> | {k}='{v}' | Text: '{el.get_text(strip=True)[:50]}'")

    # Buscar todo el HTML dentro de article.content_information o secction.content_description
    article = soup.select_one("article.content_information")
    if article:
        print("\nHTML de article.content_information:")
        print(article.prettify()[:1000])

    print("\n")
