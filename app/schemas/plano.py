"""Camada de schemas: formato dos dados que entram e saem da API (com validação)."""
import re
from typing import Any, Optional

from pydantic import BaseModel, field_validator


class PedidoPlano(BaseModel):
    local: str

    @field_validator("local")
    @classmethod
    def validar_local(cls, v: str) -> str:
        v = " ".join(v.split())  # tira quebras de linha e espaços repetidos
        if len(v) < 3:
            raise ValueError("Informe um local com pelo menos 3 caracteres.")
        if len(v) > 100:
            raise ValueError("Local muito longo (máximo 100 caracteres).")
        # Só letras, números e pontuação de endereço: barra texto que pareça instrução para a IA.
        if not re.fullmatch(r"[\w\s,.\-'ºª/]+", v):
            raise ValueError("Use apenas letras, números e pontuação simples (vírgula, ponto, hífen).")
        return v


class RegraDisparada(BaseModel):
    regra: str
    pontos: int
    explicacao: str


class ChamadaFerramenta(BaseModel):
    ferramenta: str
    argumentos: dict[str, Any]
    resultado: Any
    segundos: float


class RespostaPlano(BaseModel):
    plano: str
    chance: Optional[int] = None
    veredito: Optional[str] = None
    regras_disparadas: list[RegraDisparada] = []
    ferramentas_usadas: list[ChamadaFerramenta] = []
    segundos_total: float = 0
