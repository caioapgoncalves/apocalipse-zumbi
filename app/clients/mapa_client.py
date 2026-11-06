"""Camada de infraestrutura — OpenStreetMap (Nominatim para endereço, Overpass para locais).

Só faz requisições e devolve dados crus. Qualquer falha vira ErroServicoExterno.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.core import config
from app.core.excecoes import ErroServicoExterno

TIPOS = ["mercado", "farmacia", "hospital", "posto"]


def geocodificar(local: str) -> dict | None:
    """Devolve {latitude, longitude, nome} ou None se o local não existir."""
    try:
        r = requests.get(
            config.URL_NOMINATIM,
            params={"q": local, "format": "json", "limit": 1, "countrycodes": "br",
                    "accept-language": "pt-BR"},
            headers=config.HEADERS_HTTP, timeout=config.TIMEOUT_HTTP_S,
        )
        r.raise_for_status()
        dados = r.json()
    except (requests.RequestException, ValueError) as e:
        raise ErroServicoExterno(f"Falha ao buscar o endereço: {e}") from e

    if not dados:
        return None
    return {"latitude": float(dados[0]["lat"]), "longitude": float(dados[0]["lon"]),
            "nome": dados[0]["display_name"]}


def buscar_pontos(latitude: float, longitude: float) -> list[dict]:
    """Busca mercados, farmácias, hospitais e postos de uma vez só (1 requisição).

    Devolve [{tipo, nome, lat, lon}].
    """
    raio, lat, lon = config.RAIO_BUSCA_M, latitude, longitude
    filtros = [
        '["shop"="supermarket"]',
        '["shop"="convenience"]',
        '["amenity"="pharmacy"]',
        '["amenity"="hospital"]',
        '["amenity"="clinic"]',
        '["amenity"="fuel"]',
    ]
    partes = "".join(f"nwr{f}(around:{raio},{lat},{lon});" for f in filtros)
    consulta = f"[out:json][timeout:{config.TIMEOUT_OVERPASS_S}];({partes});out center tags;"

    elementos = _consultar_overpass(consulta)

    pontos = []
    for el in elementos:
        tags = el.get("tags", {})
        tipo = _classificar(tags)
        p_lat = el.get("lat") or el.get("center", {}).get("lat")
        p_lon = el.get("lon") or el.get("center", {}).get("lon")
        if tipo and p_lat is not None and p_lon is not None:
            pontos.append({"tipo": tipo, "nome": tags.get("name", "(sem nome)"),
                           "lat": p_lat, "lon": p_lon})
    return pontos


def _classificar(tags: dict) -> str | None:
    if tags.get("shop") in ("supermarket", "convenience"):
        return "mercado"
    amenity = tags.get("amenity")
    if amenity == "pharmacy":
        return "farmacia"
    if amenity in ("hospital", "clinic"):
        return "hospital"
    if amenity == "fuel":
        return "posto"
    return None


_cache: dict[str, list] = {}


def _consultar_overpass(consulta: str) -> list:
    """Consulta todos os servidores do Overpass ao mesmo tempo e usa o primeiro que responder."""
    if consulta in _cache:
        return _cache[consulta]

    def pedir(url: str) -> list:
        r = requests.post(url, data={"data": consulta}, headers=config.HEADERS_HTTP,
                          timeout=config.TIMEOUT_OVERPASS_S + 5)
        r.raise_for_status()
        return r.json()["elements"]

    erros = []
    pool = ThreadPoolExecutor(max_workers=len(config.URLS_OVERPASS))
    futuros = {pool.submit(pedir, url): url for url in config.URLS_OVERPASS}
    try:
        for futuro in as_completed(futuros):
            try:
                _cache[consulta] = futuro.result()
                return _cache[consulta]
            except (requests.RequestException, ValueError, KeyError) as e:
                erros.append(f"{futuros[futuro].split('/')[2]}: {type(e).__name__}")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)  # não espera os servidores mais lentos
    raise ErroServicoExterno("Todos os servidores de mapa falharam: " + "; ".join(erros))
