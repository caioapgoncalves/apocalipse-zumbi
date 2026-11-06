"""Camada de configuração: tudo que pode mudar sem mexer no código."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

GOOGLE_API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()
MODELO_GEMINI = (os.getenv("MODELO_GEMINI") or "gemini-2.5-flash").strip()
TIMEOUT_GEMINI_S = 60
MAX_ETAPAS_FUNCTION_CALLING = 8

RAIO_BUSCA_M = 2000
TIMEOUT_HTTP_S = 15
TIMEOUT_OVERPASS_S = 25  # o Overpass público é lento; consulta pesada precisa de mais tempo
HEADERS_HTTP = {"User-Agent": "plano-anti-zumbi/2.0 (trabalho academico)"}

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
URL_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# Servidores públicos do Overpass: se um estiver lento ou fora, tenta o próximo.
URLS_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

ARQUIVO_FRONTEND = RAIZ / "frontend" / "index.html"
