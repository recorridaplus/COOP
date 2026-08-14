import httpx
import json

urls_to_test = [
    "https://www.tiendainglesa.com.uy/api/catalog_system/pub/products/search?ft=conaprole&_from=0&_to=49",
    "https://tiendainglesauy.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft=conaprole&_from=0&_to=49",
    "https://www.tiendainglesa.com.uy/supermercado/busqueda?ft=conaprole"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

for url in urls_to_test:
    print(f"Probando {url}...")
    try:
        resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
        print("  Status:", resp.status_code)
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  Es JSON! Retornó {len(data)} elementos.")
                if len(data) > 0 and "productName" in data[0]:
                    print("  Primer producto:", data[0].get("productName"))
                    items = data[0].get("items", [])
                    if items and "images" in items[0]:
                        print("  Imagen:", items[0]["images"][0].get("imageUrl"))
            except Exception as e:
                print("  No es JSON válido:", str(e)[:100])
    except Exception as e:
        print("  Error:", e)
    print("-" * 50)
