import httpx
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

test_urls = {
    "tiendainglesa": [
        "https://www.tiendainglesa.com.uy/busqueda?ft=leche+conaprole",
    ],
    "tata": [
        "https://www.tata.com.uy/conaprole",
        "https://www.tata.com.uy/busca?ft=conaprole",
    ],
    "disco": [
        "https://www.disco.com.uy/conaprole",
        "https://www.disco.com.uy/buscar?text=conaprole",
    ],
    "devoto": [
        "https://www.devoto.com.uy/conaprole",
        "https://www.devoto.com.uy/buscar?text=conaprole",
    ],
    "geant": [
        "https://www.geant.com.uy/conaprole",
        "https://www.geant.com.uy/buscar?text=conaprole",
    ],
    "eldorado": [
        "https://www.eldorado.com.uy/buscar?q=conaprole",
        "https://www.eldorado.com.uy/busqueda?q=conaprole",
    ]
}

with httpx.Client(follow_redirects=True, headers=headers, timeout=12) as client:
    for name, urls in test_urls.items():
        print(f"\n==================== {name.upper()} ====================")
        for url in urls:
            try:
                r = client.get(url)
                print(f"URL: {url} -> Status: {r.status_code}, Bytes: {len(r.content)}")
                soup = BeautifulSoup(r.text, "lxml")
                
                # Check for images or product cards
                imgs = [img.get('src') or img.get('data-src') for img in soup.find_all('img') if img.get('src') or img.get('data-src')]
                print(f"  Total images found: {len(imgs)}")
                if imgs:
                    print(f"  Sample image: {imgs[0]}")
                
                # Look for product titles or product links
                prods = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    txt = a.get_text(strip=True)
                    if 'conaprole' in href.lower() or 'conaprole' in txt.lower() or '.producto' in href or '/p' in href:
                        prods.append((txt[:40], href[:60]))
                
                print(f"  Potential product matches: {len(prods)}")
                for txt, href in prods[:3]:
                    print(f"    - '{txt}' -> {href}")
                    
            except Exception as e:
                print(f"  Error fetching {url}: {e}")
