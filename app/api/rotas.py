"""Camada de API (apresentação) — recebe HTTP, chama o serviço e traduz erros em status HTTP."""
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request

from app.core.excecoes import ErroConfiguracao, ErroIA
from app.schemas.plano import PedidoPlano, RespostaPlano
from app.services import plano_service

router = APIRouter()

# Limite simples em memória: cada IP pode fazer 6 pedidos por minuto (cada um gasta cota do Gemini).
_LIMITE, _JANELA_S = 6, 60
_pedidos: dict[str, deque] = defaultdict(deque)


def _checar_limite(ip: str) -> None:
    agora, fila = time.monotonic(), _pedidos[ip]
    while fila and agora - fila[0] > _JANELA_S:
        fila.popleft()
    if len(fila) >= _LIMITE:
        raise HTTPException(429, "Muitos pedidos. Aguarde um minuto e tente de novo.")
    fila.append(agora)


@router.post("/plano", response_model=RespostaPlano)
def gerar_plano(pedido: PedidoPlano, request: Request):
    _checar_limite(request.client.host if request.client else "?")
    try:
        return plano_service.gerar_plano(pedido.local)
    except ErroConfiguracao as e:
        raise HTTPException(500, str(e))
    except ErroIA as e:
        raise HTTPException(502, str(e))
