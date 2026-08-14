import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

accounts = [
    "tiendainglesa",
    "tiendainglesauy",
    "tata",
    "tatauy",
    "tatabarato",
    "eldorado",
    "eldoradouy",
    "disco",
    "devoto",
    "geant",
    "geantuy"
]

for acc in accounts:
    url = f"https://{acc}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft=conaprole"
    try:
        r = httpx.get(url, headers=headers, timeout=8, follow_redirects=True)
        print(f"Account '{acc}': Status {r.status_code}")
        if r.status_code in [200, 206]:
            data = r.json()
            print(f"  --> ÉXITO! {len(data)} productos devueltos para '{acc}'.")
            if data:
                print(f"      Ejemplo: {data[0].get('productName')} | Link: {data[0].get('link')}")
    except Exception as e:
        print(f"Account '{acc}': Error {e}")
