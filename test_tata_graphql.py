import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
}

# Probamos la API GraphQL de TATA que vimos en Playwright
url = "https://www.tata.com.uy/api/graphql?operationName=ProductsQuery"

variables = {
    "first": 50,
    "after": "0",
    "sort": "score_desc",
    "term": "",
    "selectedFacets": [
        {"key": "brand", "value": "conaprole"},
        {"key": "locale", "value": "es-uy"}
    ]
}

print("Probando GraphQL TATA con marca 'conaprole'...")
try:
    r = httpx.get(f"{url}&variables={json.dumps(variables)}", headers=headers, timeout=10)
    print("Status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        prods = data.get("data", {}).get("products", {}).get("edges", [])
        print(f"Productos devueltos: {len(prods)}")
        if prods:
            node = prods[0].get("node", {})
            print("  Ejemplo:", node.get("name"))
            print("  Brand:", node.get("brand"))
            print("  Image:", node.get("items", [{}])[0].get("images", [{}])[0].get("url"))
    else:
        print("Error:", r.text[:200])
except Exception as e:
    print("Excepción:", e)
