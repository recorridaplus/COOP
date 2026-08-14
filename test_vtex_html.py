import httpx
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
}

for domain in ["tiendainglesa.com.uy", "tata.com.uy"]:
    url = f"https://www.{domain}/busqueda?ft=Conaprole"
    print(f"\n--- Probando HTML de búsqueda en {domain}: {url} ---")
    try:
        r = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
        print(f"Status: {r.status_code}, Length: {len(r.text)}")
        soup = BeautifulSoup(r.text, "lxml")

        # Buscar ld+json
        ld_jsons = soup.find_all("script", type="application/ld+json")
        print(f"  Scripts ld+json: {len(ld_jsons)}")
        for idx, s in enumerate(ld_jsons):
            print(f"    [{idx}] {s.text[:120]}...")

        # Buscar enlaces a productos
        links = soup.find_all("a", href=lambda h: h and ("/p" in h or "/producto" in h))
        print(f"  Enlaces a productos: {len(links)}")
        if links:
            print(f"    Ejemplo link: {links[0].get('href')}")
    except Exception as e:
        print(f"Error: {e}")
