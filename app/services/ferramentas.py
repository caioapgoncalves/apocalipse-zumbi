"""Camada de serviço — as ferramentas do function calling.

Duas partes:
1. DECLARACOES: o "cardápio" enviado ao Gemini (nome, descrição e parâmetros).
   O Gemini lê isso para decidir QUAL função pedir e COM QUAIS argumentos.
2. executar(): o nosso código roda a função pedida, usando clients e domínio.
   Erros viram {"erro": ...} para o Gemini avisar o usuário em vez de quebrar.
"""
from google.genai import types

from app.clients import clima_client, mapa_client
from app.core.excecoes import ErroServicoExterno
from app.domain import geo, regras

_COORDS = {
    "latitude": {"type": "number", "description": "Latitude do ponto."},
    "longitude": {"type": "number", "description": "Longitude do ponto."},
}

DECLARACOES = [
    types.FunctionDeclaration(
        name="geocodificar",
        description="Converte um endereço, bairro ou cidade em latitude e longitude. "
                    "Deve ser a PRIMEIRA função chamada.",
        parameters_json_schema={
            "type": "object",
            "properties": {"local": {"type": "string",
                                     "description": "Texto do usuário, ex.: 'Centro, Araraquara'."}},
            "required": ["local"],
        },
    ),
    types.FunctionDeclaration(
        name="buscar_locais_proximos",
        description="Busca, num raio de 2 km, os mercados, farmácias, hospitais e postos "
                    "de combustível mais próximos, com nome e distância em metros.",
        parameters_json_schema={"type": "object", "properties": _COORDS,
                                "required": ["latitude", "longitude"]},
    ),
    types.FunctionDeclaration(
        name="ver_clima",
        description="Consulta o clima atual: temperatura (°C), chuva (mm) e vento (km/h).",
        parameters_json_schema={"type": "object", "properties": _COORDS,
                                "required": ["latitude", "longitude"]},
    ),
    types.FunctionDeclaration(
        name="calcular_chance_sobrevivencia",
        description="Calcula a chance de sobrevivência (0 a 100) com o sistema especialista. "
                    "Chame depois de buscar_locais_proximos e ver_clima. "
                    "Use 99999 na distância de um tipo que não foi encontrado.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "dist_mercado_m": {"type": "number", "description": "Distância do mercado mais próximo (m)."},
                "dist_farmacia_m": {"type": "number", "description": "Distância da farmácia mais próxima (m)."},
                "dist_hospital_m": {"type": "number", "description": "Distância do hospital mais próximo (m)."},
                "dist_posto_m": {"type": "number", "description": "Distância do posto mais próximo (m)."},
                "chuva_mm": {"type": "number", "description": "Chuva atual (mm)."},
                "temperatura_c": {"type": "number", "description": "Temperatura atual (°C)."},
            },
            "required": ["dist_mercado_m", "dist_farmacia_m", "dist_hospital_m",
                         "dist_posto_m", "chuva_mm", "temperatura_c"],
        },
    ),
]


# ---------- Implementações ----------

def _geocodificar(local: str) -> dict:
    res = mapa_client.geocodificar(local)
    return res or {"erro": "Local não encontrado. Peça ao usuário para incluir a cidade."}


def _buscar_locais_proximos(latitude: float, longitude: float) -> dict:
    pontos = mapa_client.buscar_pontos(latitude, longitude)
    resultado = {}
    for tipo in mapa_client.TIPOS:
        locais = sorted(
            ({"nome": p["nome"], "distancia_m": geo.distancia_m(latitude, longitude, p["lat"], p["lon"])}
             for p in pontos if p["tipo"] == tipo),
            key=lambda x: x["distancia_m"],
        )
        resultado[tipo] = {
            "encontrados": len(locais),
            "mais_proximos": locais[:3],
            "distancia_mais_proximo_m": locais[0]["distancia_m"] if locais else regras.NAO_ENCONTRADO,
        }
    return resultado


def _ver_clima(latitude: float, longitude: float) -> dict:
    return clima_client.clima_atual(latitude, longitude)


def _calcular_chance_sobrevivencia(**fatos) -> dict:
    return regras.avaliar(fatos)


_IMPLEMENTACOES = {
    "geocodificar": _geocodificar,
    "buscar_locais_proximos": _buscar_locais_proximos,
    "ver_clima": _ver_clima,
    "calcular_chance_sobrevivencia": _calcular_chance_sobrevivencia,
}


def executar(nome: str, argumentos: dict) -> dict:
    """Executa a função que o Gemini pediu. Nunca lança erro: devolve {"erro": ...}."""
    funcao = _IMPLEMENTACOES.get(nome)
    if funcao is None:
        return {"erro": f"Função desconhecida: {nome}"}
    try:
        return funcao(**argumentos)
    except ErroServicoExterno as e:
        return {"erro": str(e)}
    except (TypeError, ValueError) as e:
        return {"erro": f"Argumentos inválidos para {nome}: {e}"}
