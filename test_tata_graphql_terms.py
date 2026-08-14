import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
}

url = "https://www.tata.com.uy/api/graphql?operationName=ProductsQuery"

def test_query(term="", selectedFacets=[]):
    variables = {
        "first": 50,
        "after": "0",
        "sort": "score_desc",
        "term": term,
        "selectedFacets": selectedFacets
    }
    r = httpx.get(f"{url}&variables={json.dumps(variables)}", headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        # Imprimir estructura de respuesta
        print(f"Term: '{term}', Facets: {selectedFacets}")
        prods_data = data.get("data", {}).get("products", {})
        print("  Keys:", list(prods_data.keys()))
        products = prods_data.get("products", []) or prods_data.get("edges", [])
        print(f"  Resultados: {len(products)}")
        if products:
            item = products[0]
            if "node" in item: item = item["node"]
            print(f"  Ejemplo: {item.get('name') or item.get('productName')} | Brand: {item.get('brand')}")

test_query(term="conaprole")
test_query(term="colet")
test_query(term="leche")
