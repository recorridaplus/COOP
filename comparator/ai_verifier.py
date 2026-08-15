"""
ai_verifier.py — Módulo de verificación visual inteligente con OpenAI (GPT-4o / GPT-4o-mini).

Inspecciona imágenes de packaging y etiquetas para resolver discrepancias de presentación,
variedad, lectura de gramos/ml y rediseños de envase.
"""

import os
import json
import logging
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

def is_openai_available() -> bool:
    """Retorna True si hay una clave de API de OpenAI válida configurada en el entorno."""
    return bool(OPENAI_API_KEY and len(OPENAI_API_KEY) > 10)

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

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
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
        user_content.append({
            "type": "image_url",
            "image_url": {"url": off_img, "detail": "low"}
        })

    if sup_img:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": sup_img, "detail": "low"}
        })

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
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
        ai_data["model_used"] = OPENAI_MODEL
        return ai_data

    except Exception as e:
        logger.warning(f"Error consultando API de OpenAI Vision: {e}")
        return {
            "status": "ERROR",
            "error": str(e)
        }
