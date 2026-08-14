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

app = FastAPI(title="COOP — Comparador de Catálogo Conaprole", version="1.0.0")

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

# Servir archivos estáticos del frontend
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
        # Si no existe reporte aún, generar uno preliminar
        try:
            return run_matching(compare_images_flag=False)
        except Exception as e:
            return {"discrepancies": [], "matches_summary": {}, "error": str(e)}

    with open(REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/run-comparison")
def trigger_comparison(background_tasks: BackgroundTasks):
    try:
        report = run_matching(compare_images_flag=False)
        return {"status": "ok", "message": "Comparación completada.", "summary": report.get("matches_summary")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/excel")
def download_excel():
    if not REPORT_PATH.exists():
        run_matching(compare_images_flag=False)
    excel_path = export_to_excel(REPORT_PATH)
    return FileResponse(excel_path, filename="reporte_diferencias_conaprole.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/api/export/pdf")
def download_pdf():
    if not REPORT_PATH.exists():
        run_matching(compare_images_flag=False)
    pdf_path = export_to_pdf(REPORT_PATH)
    return FileResponse(pdf_path, filename="reporte_diferencias_conaprole.pdf", media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
