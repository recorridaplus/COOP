"""
main.py — API Backend con FastAPI para el Dashboard de COOP.
"""

import json
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))
from comparator.matcher import run_matching
from reporter.excel_reporter import export_to_excel
from reporter.pdf_reporter import export_to_pdf
from scraper.conaprole_scraper import scrape_conaprole
from scraper.vtex_scraper import run_vtex_scrapers
from scraper.gdu_scraper import scrape_and_save_gdu

app = FastAPI(title="COOP — Comparador de Catálogo Conaprole", version="1.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
CONAPROLE_PATH = DATA_DIR / "conaprole_catalog.json"
REPORT_PATH = DATA_DIR / "latest_comparison_report.json"

# Estado global del scraping completo
scraping_status = {
    "is_running": False,
    "current_step": "Idle",
    "last_completed": None
}

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def read_root():
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return {"message": "COOP API activa. Ir a /docs para la documentación."}

@app.get("/api/catalog")
def get_conaprole_catalog():
    if not CONAPROLE_PATH.exists():
        raise HTTPException(status_code=404, detail="Catálogo de Conaprole no encontrado.")
    with open(CONAPROLE_PATH, encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/report")
def get_latest_report():
    if not REPORT_PATH.exists():
        try:
            return run_matching(compare_images_flag=True, use_ai_flag=True)
        except Exception as e:
            return {"discrepancies": [], "matches_summary": {}, "error": str(e)}

    with open(REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/status")
def get_scraping_status():
    return scraping_status

@app.post("/api/run-comparison")
def trigger_comparison():
    """Ejecuta únicamente el motor de re-comparación rápida sobre los datos actuales."""
    try:
        report = run_matching(compare_images_flag=True, use_ai_flag=True)
        return {"status": "ok", "message": "Re-comparación rápida completada.", "summary": report.get("matches_summary")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _execute_full_rescrape_task():
    global scraping_status
    scraping_status["is_running"] = True
    try:
        scraping_status["current_step"] = "Scrapeando supermercados (VTEX)..."
        run_vtex_scrapers()

        scraping_status["current_step"] = "Scrapeando supermercados (GDU)..."
        scrape_and_save_gdu()

        scraping_status["current_step"] = "Ejecutando motor de matching e imágenes..."
        run_matching(compare_images_flag=True, use_ai_flag=True)

        scraping_status["current_step"] = "Finalizado"
    except Exception as e:
        scraping_status["current_step"] = f"Error: {e}"
    finally:
        scraping_status["is_running"] = False

@app.post("/api/run-full-rescrape")
def trigger_full_rescrape(background_tasks: BackgroundTasks):
    """Dispara el recorrido completo de scraping de supermercados y re-comparación."""
    global scraping_status
    if scraping_status["is_running"]:
        return {"status": "busy", "message": "Ya hay un recorrido completo en ejecución.", "step": scraping_status["current_step"]}

    background_tasks.add_task(_execute_full_rescrape_task)
    return {"status": "started", "message": "Recorrido completo iniciado en segundo plano."}

@app.get("/api/export/excel")
def download_excel():
    if not REPORT_PATH.exists():
        run_matching(compare_images_flag=True, use_ai_flag=True)
    excel_path = export_to_excel(REPORT_PATH)
    return FileResponse(excel_path, filename="reporte_diferencias_conaprole.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/api/export/pdf")
def download_pdf():
    if not REPORT_PATH.exists():
        run_matching(compare_images_flag=True, use_ai_flag=True)
    pdf_path = export_to_pdf(REPORT_PATH)
    return FileResponse(pdf_path, filename="reporte_diferencias_conaprole.pdf", media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
