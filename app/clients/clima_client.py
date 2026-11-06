"""Camada de infraestrutura — Open-Meteo (clima atual, sem chave)."""
import requests

from app.core import config
from app.core.excecoes import ErroServicoExterno


def clima_atual(latitude: float, longitude: float) -> dict:
    """Devolve {temperatura_c, chuva_mm, vento_kmh}."""
    try:
        r = requests.get(
            config.URL_OPEN_METEO,
            params={"latitude": latitude, "longitude": longitude,
                    "current": "temperature_2m,precipitation,wind_speed_10m"},
            headers=config.HEADERS_HTTP, timeout=config.TIMEOUT_HTTP_S,
        )
        r.raise_for_status()
        atual = r.json()["current"]
    except (requests.RequestException, KeyError, ValueError) as e:
        raise ErroServicoExterno(f"Falha ao consultar o clima: {e}") from e

    return {"temperatura_c": atual["temperature_2m"], "chuva_mm": atual["precipitation"],
            "vento_kmh": atual["wind_speed_10m"]}
