import logging
import traceback
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api.main import _execute_full_rescrape_task, scraping_status

logging.basicConfig(level=logging.INFO)
print("Ejecutando _execute_full_rescrape_task en seco...")

try:
    _execute_full_rescrape_task()
    print("Estado final:", scraping_status)
except Exception as e:
    print("Excepción capturada:", e)
    traceback.print_exc()
