"""
ai_verifier.py — Módulo de verificación visual inteligente con OpenAI (GPT-4o / GPT-4o-mini).

Inspecciona imágenes de packaging y etiquetas para resolver discrepancias de presentación,
variedad, lectura de gramos/ml y rediseños de envase.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).parent.parent / ".env"

try:
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()
except ImportError:
    pass

def get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key and ENV_PATH.exists():
        try:
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    return key


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

def is_openai_available() -> bool:
    """Retorna True si hay una clave de API de OpenAI válida configurada en el entorno."""
    key = get_openai_api_key()
    return bool(key and len(key) > 10 and not key.startswith("your_"))


import base64
import io
from comparator.image_comparator import fetch_image

def pil_to_base64_url(pil_img) -> str | None:
    if not pil_img:
        return None
    try:
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        logger.warning(f"Error convirtiendo imagen a base64: {e}")
        return None

def verify_product_match_with_ai(
    official_prod: dict,
    supermarket_prod: dict,
    current_img_cmp: dict | None = None
) -> dict:
    """
    Verifica un par de productos (oficial vs supermercado) utilizando OpenAI Vision.
    Inspecciona los títulos, descripciones y las fotos de los packagings para leer etiquetas.
    
    Retorna un diccionario estructurado con el dictamen de la IA.
    """
    if not is_openai_available():
        return {
            "status": "SKIPPED",
            "reason": "OPENAI_API_KEY no está configurada en el entorno."
        }

    api_key = get_openai_api_key()
    model_name = get_openai_model()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Error inicializando cliente de OpenAI: {e}")
        return {
            "status": "ERROR",
            "error": str(e)
        }

    off_name = official_prod.get("name", "")
    off_cat = official_prod.get("category", "")
    off_desc = official_prod.get("description", "")
    off_img = official_prod.get("images", [""])[0] if official_prod.get("images") else ""

    sup_name = supermarket_prod.get("name", "")
    sup_desc = supermarket_prod.get("description", "")
    sup_img = supermarket_prod.get("image_url", "")

    # Construir contenido del mensaje multimodal
    user_content = [
        {
            "type": "text",
            "text": (
                "Compara los siguientes dos productos (catálogo oficial Conaprole vs publicación en supermercado):\n\n"
                f"--- PRODUCTO OFICIAL CONAPROLE ---\n"
                f"Nombre: {off_name}\n"
                f"Categoría: {off_cat}\n"
                f"Descripción: {off_desc[:200] if off_desc else 'N/A'}\n\n"
                f"--- PRODUCTO EN SUPERMERCADO ---\n"
                f"Nombre publicado: {sup_name}\n"
                f"Descripción: {sup_desc[:200] if sup_desc else 'N/A'}\n\n"
                "Por favor analiza las imágenes de los packagings (si están disponibles) y el texto. "
                "Responde EXCLUSIVAMENTE en formato JSON con la siguiente estructura exacta:\n"
                "{\n"
                '  "is_same_product": true|false,\n'
                '  "is_same_presentation": true|false,\n'
                '  "official_label_info": "información o gramos/ml leídos en envase oficial",\n'
                '  "supermarket_label_info": "información o gramos/ml leídos en envase supermercado",\n'
                '  "ai_verdict": "MATCH" | "DIFFERENT_PRESENTATION" | "DIFFERENT_FLAVOR" | "PACKAGING_REDESIGN" | "APOCRYPHAL_IMAGE",\n'
                '  "suggested_alert_level": "NONE" | "BLUE" | "YELLOW" | "RED",\n'
                '  "explanation": "breve justificación de tu dictamen en español"\n'
                "}"
            )
        }
    ]

    if off_img:
        pil_off = fetch_image(off_img)
        if pil_off:
            b64_off = pil_to_base64_url(pil_off)
            if b64_off:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": b64_off, "detail": "low"}
                })

    if sup_img:
        pil_sup = fetch_image(sup_img)
        if pil_sup:
            b64_sup = pil_to_base64_url(pil_sup)
            if b64_sup:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": b64_sup, "detail": "low"}
                })



    import time
    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=model_name,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un experto auditor de catálogo de productos lácteos y supermercados para Conaprole Uruguay. "
                            "Tu objetivo es inspeccionar el packaging, etiquetas (gramos, ml, porcentaje grasa, sabor) y determinar "
                            "si el producto publicado en el supermercado coincide exactamente con el producto oficial."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                temperature=0.1,
                max_tokens=400
            )

            result_text = response.choices[0].message.content
            ai_data = json.loads(result_text)
            ai_data["status"] = "SUCCESS"
            ai_data["model_used"] = model_name
            return ai_data

        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "rate_limit" in err_str.lower()) and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            logger.warning(f"Error consultando API de OpenAI Vision: {e}")
            return {
                "status": "ERROR",
                "error": err_str
            }

