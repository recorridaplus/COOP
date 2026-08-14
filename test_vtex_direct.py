import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def test_api(url):
    print(f"\n--- Probando: {url} ---")
    try:
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"Array devuelto ({len(data)} elementos)")
                if data:
                    print("  Primer item:", data[0].get("productName"), "| Brand:", data[0].get("brand"))
            elif isinstance(data, dict):
                print("Dict devuelto keys:", list(data.keys()))
        else:
            print(f"Error {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"Excepción: {e}")

test_api("https://www.tiendainglesa.com.uy/api/catalog_system/pub/products/search?ft=conaprole")
test_api("https://www.tata.com.uy/api/catalog_system/pub/products/search?ft=conaprole")
test_api("https://www.eldorado.com.uy/api/catalog_system/pub/products/search?ft=conaprole")
