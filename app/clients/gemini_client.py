"""Camada de infraestrutura — acesso ao Gemini (SDK google-genai).

Só envia a conversa e devolve a resposta. Quem decide o que fazer com
os pedidos de função é a camada de serviço (agente_service.py).
"""
from google import genai
from google.genai import types

from app.core import config
from app.core.excecoes import ErroConfiguracao, ErroIA

_clients: dict[int, genai.Client] = {}


def _obter_client(timeout_s: int = config.TIMEOUT_GEMINI_S) -> genai.Client:
    if not config.GOOGLE_API_KEY or config.GOOGLE_API_KEY == "cole_sua_chave_aqui":
        raise ErroConfiguracao("GOOGLE_API_KEY não configurada no arquivo .env")
    if timeout_s not in _clients:
        _clients[timeout_s] = genai.Client(
            api_key=config.GOOGLE_API_KEY,
            http_options=types.HttpOptions(
                timeout=timeout_s * 1000,
                # 1 tentativa só: se travar, falha rápido com mensagem clara.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
    return _clients[timeout_s]


def _pensamento(modelo: str) -> types.ThinkingConfig | None:
    """Modelos Gemini 3 'pensam' antes de responder; nível baixo deixa bem mais rápido."""
    if modelo.startswith("gemini-3"):
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
    return None


def gerar(conteudos: list, instrucoes: str, declaracoes: list) -> types.GenerateContentResponse:
    """Envia a conversa ao Gemini informando quais funções ele pode pedir."""
    cfg = types.GenerateContentConfig(
        system_instruction=instrucoes,
        tools=[types.Tool(function_declarations=declaracoes)],
        # Desligado de propósito: o nosso código executa as funções (loop manual),
        # assim cada etapa fica visível no log e no front-end.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=_pensamento(config.MODELO_GEMINI),
    )
    client = _obter_client()  # fora do try: falta de chave é erro de configuração, não do Gemini
    try:
        return client.models.generate_content(
            model=config.MODELO_GEMINI, contents=conteudos, config=cfg)
    except Exception as e:
        raise ErroIA(f"Erro ao falar com o Gemini ({config.MODELO_GEMINI}): {_resumo(e)}") from e


def testar_modelo(modelo: str, timeout_s: int = 45) -> str:
    """Usado pelo diagnóstico: pergunta simples, sem funções."""
    client = _obter_client(timeout_s)
    try:
        r = client.models.generate_content(
            model=modelo, contents="Responda apenas: ok",
            config=types.GenerateContentConfig(thinking_config=_pensamento(modelo)))
        return (r.text or "").strip()
    except Exception as e:
        raise ErroIA(_resumo(e)) from e


def listar_modelos_flash() -> list[str]:
    """Usado pelo diagnóstico: modelos 'flash' que geram texto, disponíveis para a sua chave."""
    nomes = []
    for m in _obter_client(20).models.list():
        acoes = getattr(m, "supported_actions", None) or []
        nome = m.name.replace("models/", "")
        if "flash" in nome and (not acoes or "generateContent" in acoes) \
                and not any(x in nome for x in ("image", "tts", "audio", "live", "embedding")):
            nomes.append(nome)
    return sorted(nomes, reverse=True)


def _resumo(e: Exception) -> str:
    nome = type(e).__name__
    if "Timeout" in nome:
        return "o Gemini demorou demais para responder (timeout). Rode o diagnostico.py para escolher outro modelo."
    return f"{nome}: {str(e)[:300]}"