"""Erros próprios da aplicação. Cada camada lança o seu; a camada de API traduz para HTTP."""


class ErroServicoExterno(Exception):
    """Uma API externa (mapa, clima) falhou ou respondeu algo inesperado."""


class ErroConfiguracao(Exception):
    """Falta alguma configuração obrigatória (ex.: chave do Gemini)."""


class ErroIA(Exception):
    """Falha na comunicação com o Gemini."""
