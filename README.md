# COOP — Comparador de Catálogo Conaprole vs. Supermercados

Herramienta para monitorear y comparar cómo los supermercados uruguayos publican los productos de Conaprole, detectando diferencias en imágenes, nombres y descripciones respecto al catálogo oficial.

## Supermercados cubiertos

| Supermercado | Plataforma | Estrategia |
|---|---|---|
| Tienda Inglesa | VTEX IO | API VTEX |
| TATA | VTEX IO | API VTEX |
| Géant | Blazor/.NET (GDU) | httpx + BeautifulSoup |
| Disco | Blazor/.NET (GDU) | httpx + BeautifulSoup |
| Devoto | Blazor/.NET (GDU) | httpx + BeautifulSoup |
| El Dorado | Scanntech | httpx + BeautifulSoup |

## Estructura del proyecto

```
COOP/
├── scraper/
│   ├── conaprole_scraper.py     # Catálogo oficial (fuente de verdad)
│   ├── vtex_scraper.py          # Tienda Inglesa, TATA
│   ├── gdu_scraper.py           # Géant, Disco, Devoto
│   ├── eldorado_scraper.py      # El Dorado
│   └── rate_limiter.py          # Control de delays y cortesía
├── comparator/
│   ├── image_comparator.py      # pHash + análisis de fondo/iluminación
│   ├── text_comparator.py       # Similitud de nombre/descripción
│   └── matcher.py               # Matching de productos entre catálogos
├── reporter/
│   ├── pdf_reporter.py          # Reporte exportable en PDF
│   ├── excel_reporter.py        # Reporte exportable en Excel
│   └── notifier.py              # Envío de email/alerta
├── data/
│   ├── conaprole_catalog.json   # Catálogo Conaprole (generado)
│   └── supermarkets/            # Datos por supermercado (generados)
├── frontend/
│   ├── index.html               # Dashboard de diferencias
│   ├── style.css
│   └── app.js
├── api/
│   └── main.py                  # API FastAPI
├── requirements.txt
├── .env.example
└── README.md
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# 1. Actualizar catálogo Conaprole
python scraper/conaprole_scraper.py

# 2. Scrapear todos los supermercados
python scraper/vtex_scraper.py
python scraper/gdu_scraper.py
python scraper/eldorado_scraper.py

# 3. Comparar y generar reporte
python comparator/matcher.py

# 4. Ver dashboard
python api/main.py
```

## Diseño

- **Sin historial**: cada corrida es independiente y produce un reporte fresco del estado actual.
- **Acceso responsable**: delays aleatorios entre requests, respeto de robots.txt, sin paralelismo agresivo.
- **Dos niveles de alerta de imagen**: 🟡 imagen diferente / 🔴 imagen apócrifa (foto propia del CM).
