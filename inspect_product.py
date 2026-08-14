from bs4 import BeautifulSoup

with open("scratch_product.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "lxml")

article = soup.select_one("article.content_information")
if article:
    # Primero mostrar todas las imgs dentro del artículo
    imgs = article.find_all("img")
    print(f"Imgs dentro de article.content_information: {len(imgs)}")
    for img in imgs:
        print(f"  src={img.get('src','')[:90]}")
        print(f"  class={img.get('class')} alt={img.get('alt','')[:40]}")
    
    print()
    # Mostrar estructura de texto
    print("=== TEXTO DEL ARTICLE ===")
    print(article.get_text(separator="\n", strip=True)[:800])
    
    print()
    # Mostrar h1, h2, h3
    print("=== HEADINGS ===")
    for tag in article.find_all(["h1","h2","h3"]):
        print(f"  <{tag.name}> {tag.get_text(strip=True)[:80]}")
    
    print()
    # Mostrar párrafos
    print("=== PÁRRAFOS ===")
    for p in article.find_all("p"):
        txt = p.get_text(strip=True)
        if txt:
            print(f"  {txt[:100]}")
