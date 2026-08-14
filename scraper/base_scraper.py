"""
base_scraper.py — Clase base para scrapers de supermercados.
"""

from abc import ABC, abstractmethod
from typing import TypedDict, Optional

class SupermarketProduct(TypedDict):
    name: str            # Nombre publicado por el supermercado
    image_url: str       # URL de la imagen principal
    description: str     # Descripción del producto (o vacía "")
    product_url: str     # URL del producto en el supermercado
    supermarket: str     # Nombre del supermercado (ej: "Tienda Inglesa")
    scraped_at: str      # Timestamp ISO 8601 UTC

class BaseSupermarketScraper(ABC):
    """
    Interfaz común para todos los scrapers de supermercados.
    """

    def __init__(self, supermarket_name: str, base_url: str):
        self.supermarket_name = supermarket_name
        self.base_url = base_url

    @abstractmethod
    def search_product(self, query: str) -> list[SupermarketProduct]:
        """
        Busca un término (o nombre de producto) en el supermercado y
        devuelve la lista de productos encontrados.
        """
        pass
