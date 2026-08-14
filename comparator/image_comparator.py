"""
image_comparator.py — Comparador de imágenes de productos.

Detección en 2 niveles:
1. pHash (hash perceptual) → distancia de Hamming entre hashes
2. Análisis de fondo e iluminación (si difieren):
   - Fondo estéril/blanco puro → 🟡 Imagen Diferente (otra versión/crop oficial)
   - Fondo complejo/sombras/iluminación no uniforme → 🔴 Imagen Apócrifa (foto tomada por CM)
"""

import logging
import io
from typing import TypedDict, Literal
import httpx
from PIL import Image, ImageStat
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
    """Descarga una imagen desde una URL y devuelve un objeto PIL Image."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return img
    except Exception as e:
        logger.warning(f"Error descargando imagen desde {url}: {e}")
        return None

def analyze_background(img: Image.Image) -> bool:
    """
    Analiza si el fondo de la imagen es blanco uniforme (estilo foto de estudio/catálogo oficial).
    Devuelve True si el fondo es blanco estéril (~90%+ píxeles blancos en los bordes).
    """
    width, height = img.size
    
    # Muestrear bordes de la imagen (10% exterior)
    border_pixels = []
    
    # Top and bottom borders
    for x in range(width):
        border_pixels.append(img.getpixel((x, 0)))
        border_pixels.append(img.getpixel((x, height - 1)))
        
    # Left and right borders
    for y in range(height):
        border_pixels.append(img.getpixel((0, y)))
        border_pixels.append(img.getpixel((width - 1, y)))
        
    # Contar píxeles blancos (RGB cada canal >= 240)
    white_count = sum(1 for r, g, b in border_pixels if r >= 240 and g >= 240 and b >= 240)
    white_ratio = white_count / len(border_pixels) if border_pixels else 0
    
    logger.debug(f"Ratio de fondo blanco en bordes: {white_ratio:.2%}")
    return white_ratio >= 0.85

def compare_images(
    official_url: str,
    supermarket_url: str,
    phash_threshold: int = 12
) -> ImageComparisonResult:
    """
    Compara dos URLs de imágenes.
    - phash_threshold: distancia de Hamming máxima para considerar imágenes iguales (default <= 12).
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

    # 1. pHash
    hash_off = imagehash.phash(img_off)
    hash_sup = imagehash.phash(img_sup)
    distance = hash_off - hash_sup

    if distance <= phash_threshold:
        return {
            "status": "MATCH",
            "phash_distance": distance,
            "official_url": official_url,
            "supermarket_url": supermarket_url,
            "details": f"Imagen coincidente (pHash dist: {distance})"
        }

    # 2. Si difiere → Analizar si es foto apócrifa (tomada por el CM) vs otra versión oficial
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
            "details": f"🔴 Imagen apócrifa (fondo no estéril / foto propia del supermercado, pHash dist: {distance})"
        }
