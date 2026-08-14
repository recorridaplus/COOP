import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

terms = ["leche", "queso", "yogur", "dulce", "helado", "postre", "manteca", "crema", "colet"]

def test_terms(account):
    print(f"\n==================== {account.upper()} ====================")
    total_conaprole = []
    
    # 1. Probar por marca fq=b:*
    url_b = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?fq=b:conaprole"
    r = httpx.get(url_b, headers=headers, timeout=8)
    if r.status_code in [200, 206]:
        b_prods = r.json()
        print(f"Búsqueda fq=b:conaprole -> {len(b_prods)} productos")
        total_conaprole.extend(b_prods)

    for t in terms:
        url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/products/search?ft={t}&_from=0&_to=49"
        try:
            resp = httpx.get(url, headers=headers, timeout=8)
            if resp.status_code in [200, 206]:
                prods = resp.json()
                conaprole_prods = [p for p in prods if "conaprole" in p.get("brand","").lower() or "conaprole" in p.get("productName","").lower() or "colet" in p.get("productName","").lower()]
                print(f"  Término '{t}': {len(prods)} resultados ({len(conaprole_prods)} de Conaprole)")
                for cp in conaprole_prods:
                    if not any(x["productId"] == cp["productId"] for x in total_conaprole):
                        total_conaprole.append(cp)
        except Exception as e:
            print(f"  Error en '{t}': {e}")
            
    print(f"TOTAL ÚNICOS CONAPROLE EN {account}: {len(total_conaprole)}")

test_terms("tatauy")
