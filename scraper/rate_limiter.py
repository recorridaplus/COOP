"""
rate_limiter.py — Control de cortesía para requests HTTP

Aplica delays aleatorios, respeta robots.txt y maneja reintentos
con backoff exponencial. Se usa en todos los scrapers.
"""

import time
import random
import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Headers que imitan un navegador real
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-UY,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class RateLimiter:
    """
    Gestiona el ritmo de requests hacia un dominio dado.
    - Delays aleatorios entre requests
    - Respeto de robots.txt
    - Reintentos con backoff exponencial ante 429 / 503
    """

    def __init__(
        self,
        base_url: str,
        delay_min: float = 2.0,
        delay_max: float = 5.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self._last_request_time: float = 0.0
        self._robots: RobotFileParser | None = None
        self._robots_loaded = False

    def _load_robots(self, client: httpx.Client) -> None:
        """Descarga y parsea robots.txt una sola vez."""
        if self._robots_loaded:
            return
        robots_url = f"{self.base_url.rstrip('/')}/robots.txt"
        try:
            resp = client.get(robots_url, timeout=10)
            self._robots = RobotFileParser()
            self._robots.parse(resp.text.splitlines())
            logger.debug(f"robots.txt cargado desde {robots_url}")
        except Exception as e:
            logger.warning(f"No se pudo cargar robots.txt: {e}")
            self._robots = None
        finally:
            self._robots_loaded = True

    def can_fetch(self, url: str) -> bool:
        """Verifica si robots.txt permite acceder a la URL."""
        if self._robots is None:
            return True
        return self._robots.can_fetch(DEFAULT_HEADERS["User-Agent"], url)

    def _wait(self) -> None:
        """Espera el tiempo necesario para respetar el delay entre requests."""
        elapsed = time.monotonic() - self._last_request_time
        delay = random.uniform(self.delay_min, self.delay_max)
        remaining = delay - elapsed
        if remaining > 0:
            logger.debug(f"Esperando {remaining:.2f}s...")
            time.sleep(remaining)

    def get(
        self,
        client: httpx.Client,
        url: str,
        **kwargs,
    ) -> httpx.Response | None:
        """
        Hace un GET respetando delays, robots.txt y con reintentos.
        Devuelve None si la URL no está permitida o falla tras todos los reintentos.
        """
        self._load_robots(client)

        if not self.can_fetch(url):
            logger.warning(f"robots.txt prohíbe acceder a: {url}")
            return None

        for attempt in range(1, self.max_retries + 1):
            self._wait()
            try:
                resp = client.get(url, headers=DEFAULT_HEADERS, timeout=15, **kwargs)
                self._last_request_time = time.monotonic()

                if resp.status_code == 429 or resp.status_code == 503:
                    wait_time = 2 ** attempt * 10  # backoff: 20s, 40s, 80s
                    logger.warning(
                        f"Rate limited ({resp.status_code}) en {url}. "
                        f"Esperando {wait_time}s (intento {attempt}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()
                return resp

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} en {url}: {e}")
            except httpx.RequestError as e:
                logger.error(f"Request error en {url}: {e}")

            if attempt < self.max_retries:
                wait_time = 2 ** attempt * 5
                logger.info(f"Reintentando en {wait_time}s...")
                time.sleep(wait_time)

        logger.error(f"Falló tras {self.max_retries} intentos: {url}")
        return None
