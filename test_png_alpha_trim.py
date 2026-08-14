import io
import httpx
from PIL import Image, ImageChops
import imagehash

def load_image_with_white_bg(url: str) -> Image.Image:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"}
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
    raw_img = Image.open(io.BytesIO(resp.content))
    
    # Si la imagen tiene canal Alfa / Transparencia (PNG), pegarla sobre fondo blanco
    if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
        rgba_img = raw_img.convert("RGBA")
        background = Image.new("RGBA", rgba_img.size, (255, 255, 255, 255))
        # Alfa compositing: pegar sobre blanco estéril
        composite = Image.alpha_composite(background, rgba_img)
        return composite.convert("RGB")
    else:
        return raw_img.convert("RGB")

def trim_white_background(img: Image.Image, tolerance=25) -> Image.Image:
    img_rgb = img.convert("RGB")
    bg = Image.new("RGB", img_rgb.size, (255, 255, 255))
    diff = ImageChops.difference(img_rgb, bg)
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

url_off = "https://cdn.conaprole.uy/gallery/202201/20241130194752_1667177984.png"
url_dev = "https://gdu-multimedia.azurewebsites.net/api/gdu/multimedia/03a74848-a96b-45b1-96b5-378713c0172c/content"

img_off = load_image_with_white_bg(url_off)
img_dev = load_image_with_white_bg(url_dev)

print("Original Oficial mode:", img_off.mode, "size:", img_off.size)
print("Original Devoto  mode:", img_dev.mode, "size:", img_dev.size)

trimmed_off = trim_white_background(img_off)
trimmed_dev = trim_white_background(img_dev)

print("Trimmed Oficial size:", trimmed_off.size)
print("Trimmed Devoto  size:", trimmed_dev.size)

# Resize ambos par a dimensiones idénticas antes de pHash (ej 256x256)
resized_off = trimmed_off.resize((256, 256), Image.Resampling.LANCZOS)
resized_dev = trimmed_dev.resize((256, 256), Image.Resampling.LANCZOS)

hash_off = imagehash.phash(resized_off)
hash_dev = imagehash.phash(resized_dev)
dist = hash_off - hash_dev

print(f"\nDistancia pHash tras Alpha Compositing + Trim + Resize: {dist}")
