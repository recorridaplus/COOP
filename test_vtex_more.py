import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

more_accounts = [
    "tiendainglesa",
    "tiendainglesa1",
    "tiendainglesaprod",
    "tiendainglesaio",
    "tinglesa",
    "tienda",
    "geant",
    "geantstore",
    "geantprod",
    "gdu",
    "gduuy",
    "gduprod",
    "disco",
    "discouy",
    "supermercadosdisco",
    "devoto",
    "devotouy",
]

for acc in more_accounts:
    url = f"https://{acc}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft=conaprole"
    try:
        r = httpx.get(url, headers=headers, timeout=6, follow_redirects=True)
        if r.status_code in [200, 206]:
            data = r.json()
            print(f"✅ ÉXITO! Account '{acc}': {len(data)} productos devueltos.")
            if data:
                print(f"   Ejemplo: {data[0].get('productName')} | {data[0].get('link')}")
        else:
            print(f"Account '{acc}': Status {r.status_code}")
    except Exception as e:
        print(f"Account '{acc}': Error {e}")
