"""
image_comparator.py — Comparador inteligente de imágenes de productos.

Detección en 2 niveles con Alpha Compositing y Auto-Recorte:
1. Alpha Compositing (PNG): Fusiona transparencias sobre un fondo blanco puro.
2. Auto-recorte (Trim): Recorta el lienzo sobrante aislando únicamente la botella/pote/envase.
3. Resize normalizado (256x256) antes del pHash.
4. pHash (hash perceptual) sobre el packaging aislado.
5. Detección de imágenes apócrifas (fotos de estudio/catálogo vs fotos caseras del CM).
"""

import logging
import io
from typing import TypedDict, Literal
import httpx
from PIL import Image, ImageChops
import imagehash

logger = logging.getLogger(__name__)

ImageType = Literal["MATCH", "DIFFERENT_IMAGE", "APOCRYPHAL_IMAGE", "ERROR"]

class ImageComparisonResult(TypedDict):
    status: ImageType
    phash_distance: int
    official_url: str
    supermarket_url: str
    details: str

def fetch_image(url: str, timeout: int = 10) -> Image.Image | None:
    """Descarga una imagen desde una URL y maneja transparencias (PNG Alpha Compositing)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        raw_img = Image.open(io.BytesIO(resp.content))

        # Manejar la transparencia de imágenes PNG pegándolas sobre un fondo blanco sólido
        if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
            rgba_img = raw_img.convert("RGBA")
            background = Image.new("RGBA", rgba_img.size, (255, 255, 255, 255))
            composite = Image.alpha_composite(background, rgba_img)
            return composite.convert("RGB")
        else:
            return raw_img.convert("RGB")
    except Exception as e:
        logger.warning(f"Error descargando imagen desde {url}: {e}")
        return None

def trim_white_background(img: Image.Image, tolerance: int = 25) -> Image.Image:
    """
    Recorta el fondo blanco sobrante en los 4 bordes para aislar el envase del producto.
    """
    img_rgb = img.convert("RGB")
    bg = Image.new("RGB", img_rgb.size, (255, 255, 255))
    diff = ImageChops.difference(img_rgb, bg)
    
    # Umbralizar para tolerar compresión JPEG ligera en el fondo
    diff = ImageChops.add(diff, diff, 2.0, -tolerance)
    bbox = diff.getbbox()
    
    if bbox:
        w, h = img_rgb.size
        left = max(0, bbox[0] - int(w * 0.01))
        top = max(0, bbox[1] - int(h * 0.01))
        right = min(w, bbox[2] + int(w * 0.01))
        bottom = min(h, bbox[3] + int(h * 0.01))
        return img_rgb.crop((left, top, right, bottom))
    return img_rgb

def analyze_background(img: Image.Image) -> bool:
    """
    Analiza si el fondo de la imagen es blanco uniforme (estilo foto de estudio/catálogo oficial).
    Devuelve True si el fondo es blanco estéril (~85%+ píxeles blancos en los bordes).
    """
    width, height = img.size
    border_pixels = []
    
    for x in range(width):
        border_pixels.append(img.getpixel((x, 0)))
        border_pixels.append(img.getpixel((x, height - 1)))
        
    for y in range(height):
        border_pixels.append(img.getpixel((0, y)))
        border_pixels.append(img.getpixel((width - 1, y)))
        
    white_count = sum(1 for r, g, b in border_pixels if r >= 235 and g >= 235 and b >= 235)
    white_ratio = white_count / len(border_pixels) if border_pixels else 0
    
    return white_ratio >= 0.85

def compare_images(
    official_url: str,
    supermarket_url: str,
    phash_threshold: int = 12
) -> ImageComparisonResult:
    """
    Compara dos URLs de imágenes aplicando Alpha Compositing + Trim + Normalización 256x256.
    """
    if not official_url or not supermarket_url:
        return {
            "status": "ERROR",
            "phash_distance": -1,
            "official_url": official_url or "",
            "supermarket_url": supermarket_url or "",
            "details": "URL faltante"
        }

    img_off = fetch_image(official_url)
    img_sup = fetch_image(supermarket_url)

    if not img_off or not img_sup:
        return {
            "status": "ERROR",
            "phash_distance": -1,
            "official_url": official_url,
            "supermarket_url": supermarket_url,
            "details": "No se pudo descargar una o ambas imágenes"
        }

    # 1. Aplicar Trim (recorte de fondo blanco) a ambas imágenes para aislar el envase
    trimmed_off = trim_white_background(img_off)
    trimmed_sup = trim_white_background(img_sup)

    # 2. Redimensionar ambas imágenes recortadas a 256x256 para comparativa normalizada
    resized_off = trimmed_off.resize((256, 256), Image.Resampling.LANCZOS)
    resized_sup = trimmed_sup.resize((256, 256), Image.Resampling.LANCZOS)

    # 3. pHash sobre el packaging aislado
    hash_off = imagehash.phash(resized_off)
    hash_sup = imagehash.phash(resized_sup)
    distance = int(hash_off - hash_sup)

    if distance <= phash_threshold:
        return {
            "status": "MATCH",
            "phash_distance": distance,
            "official_url": official_url,
            "supermarket_url": supermarket_url,
            "details": f"Imagen coincidente (pHash dist: {distance})"
        }

    # 4. Si aun tras el recorte el pHash difiere → Analizar si es foto apócrifa vs otra versión
    is_white_bg = analyze_background(img_sup)

    if is_white_bg:
        return {
            "status": "DIFFERENT_IMAGE",
            "phash_distance": distance,
            "official_url": official_url,
            "supermarket_url": supermarket_url,
            "details": f"🟡 Imagen diferente (fondo blanco de catálogo, pHash dist: {distance})"
        }
    else:
        return {
            "status": "APOCRYPHAL_IMAGE",
            "phash_distance": distance,
            "official_url": official_url,
            "supermarket_url": supermarket_url,
            "details": f"🔴 Imagen apócrifa (foto tomada por CM / fondo no estéril, pHash dist: {distance})"
        }
