import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_vtex_all(account, query="conaprole"):
    products = []
    _from = 0
    step = 50
    
    print(f"\n==================== VTEX {account.upper()} ({query}) ====================")
    while True:
        url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={query}&_from={_from}&_to={_from + step - 1}"
        r = httpx.get(url, headers=headers, timeout=10)
        if r.status_code not in [200, 206]:
            print(f"Fin o error HTTP {r.status_code}")
            break
        
        batch = r.json()
        if not batch:
            print("Lote vacío. Fin.")
            break
            
        print(f"Lote desde {_from} a {_from + step - 1}: {len(batch)} productos")
        products.extend(batch)
        if len(batch) < step:
            break
        _from += step
        
    print(f"TOTAL OBTENIDO PARA {account}: {len(products)} productos")
    if products:
        p = products[0]
        print("\nEjemplo de producto VTEX:")
        print("  productId:", p.get("productId"))
        print("  productName:", p.get("productName"))
        print("  brand:", p.get("brand"))
        print("  link:", p.get("link"))
        items = p.get("items", [])
        if items:
            imgs = items[0].get("images", [])
            print("  images:", [img.get("imageUrl") for img in imgs])

fetch_vtex_all("tatauy", "conaprole")
fetch_vtex_all("eldoradouy", "conaprole")
