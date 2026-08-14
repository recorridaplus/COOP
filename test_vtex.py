import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def test_vtex(domain, account_name, term):
    print(f"\n================ {domain} ({term}) ================")
    
    # 1. Probar API Catalog System
    url_cat = f"https://www.{domain}/api/catalog_system/pub/products/search/{term}"
    print(f"Probando Catalog System: {url_cat}")
    try:
        r = httpx.get(url_cat, headers=headers, timeout=10, follow_redirects=True)
        print(f"Status: {r.status_code}")
        if r.status_code == 200 and r.text.startswith("["):
            data = r.json()
            print(f"Items devueltos: {len(data)}")
            if data:
                item = data[0]
                print(f"  Nombre: {item.get('productName')}")
                print(f"  Brand: {item.get('brand')}")
                print(f"  Link: {item.get('link')}")
                items_skus = item.get('items', [])
                if items_skus:
                    imgs = items_skus[0].get('images', [])
                    print(f"  Imágenes: {[img.get('imageUrl') for img in imgs]}")
        else:
            print(f"Respuesta no válida: {r.text[:150]}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Probar Intelligent Search API
    url_is = f"https://www.{domain}/api/io/_v/api/intelligent-search/product_search/{term}"
    print(f"\nProbando Intelligent Search: {url_is}")
    try:
        r = httpx.get(url_is, headers=headers, timeout=10, follow_redirects=True)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            prods = data.get('products', [])
            print(f"Productos devueltos: {len(prods)}")
            if prods:
                p = prods[0]
                print(f"  Nombre: {p.get('productName')}")
                print(f"  Brand: {p.get('brand')}")
                print(f"  Link: {p.get('link')}")
                items_skus = p.get('items', [])
                if items_skus:
                    imgs = items_skus[0].get('images', [])
                    print(f"  Imágenes: {[img.get('imageUrl') for img in imgs]}")
    except Exception as e:
        print(f"Error: {e}")

test_vtex("tiendainglesa.com.uy", "tiendainglesa", "Conaprole")
test_vtex("tata.com.uy", "tata", "Conaprole")
