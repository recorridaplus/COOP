import sys
from pathlib import Path
from PIL import Image, ImageChops
import imagehash

sys.path.insert(0, str(Path(__file__).parent.parent))

def trim_background(img: Image.Image, bg_color=(255, 255, 255), tolerance=15) -> Image.Image:
    """
    Recorta el fondo uniforme (blanco/claro) alrededor del producto,
    dejando únicamente el área útil del packaging.
    """
    img_rgb = img.convert("RGB")
    # Crear fondo de referencia blanco
    bg = Image.new("RGB", img_rgb.size, bg_color)
    diff = ImageChops.difference(img_rgb, bg)
    
    # Umbralizar para ignorar pequeñas variaciones de compresión en el fondo
    diff = ImageChops.add(diff, diff, 2.0, -tolerance)
    bbox = diff.getbbox()
    
    if bbox:
        return img_rgb.crop(bbox)
    return img_rgb

def test_crop_demo():
    print("Prueba de recorte de padding de fondo...")
    # Crear dos imágenes de prueba: una imagen y la misma con 30% de padding extra
    img1 = Image.new("RGB", (200, 200), (255, 255, 255))
    # Dibujar un rectángulo central (producto)
    for x in range(50, 150):
        for y in range(50, 150):
            img1.putpixel((x, y), (200, 50, 50))
            
    # Imagen 2: misma foto del producto pero con canvas más grande (más fondo/crop amplio)
    img2 = Image.new("RGB", (400, 400), (255, 255, 255))
    for x in range(150, 250):
        for y in range(150, 250):
            img2.putpixel((x, y), (200, 50, 50))

    # Sin recorte
    h1_raw = imagehash.phash(img1)
    h2_raw = imagehash.phash(img2)
    dist_raw = h1_raw - h2_raw

    # Con recorte automático de fondo (trim)
    trimmed1 = trim_background(img1)
    trimmed2 = trim_background(img2)
    h1_trim = imagehash.phash(trimmed1)
    h2_trim = imagehash.phash(trimmed2)
    dist_trim = h1_trim - h2_trim

    print(f"Distancia pHash SIN recorte (con padding diferente): {dist_raw}")
    print(f"Distancia pHash CON recorte de fondo (Trim): {dist_trim}")
    print(f"Resultado Trim 1 size: {trimmed1.size}, Trim 2 size: {trimmed2.size}")

test_crop_demo()
