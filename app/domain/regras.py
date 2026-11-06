"""Camada de domínio — sistema especialista.

Regra de negócio pura: não conhece FastAPI, Gemini nem HTTP.
Base de conhecimento (REGRAS) + motor de inferência (avaliar) + explicação.
"""

PONTUACAO_BASE = 50

# Distância usada quando um tipo de local não foi encontrado no raio da busca.
NAO_ENCONTRADO = 99999

# (nome, condição, pontos, explicação)
REGRAS = [
    ("mercado_perto", lambda f: f["dist_mercado_m"] <= 500, +15,
     "SE há mercado a até 500 m ENTÃO +15 (comida na primeira semana)"),
    ("mercado_medio", lambda f: 500 < f["dist_mercado_m"] <= 1500, +7,
     "SE o mercado está entre 500 m e 1,5 km ENTÃO +7 (dá para ir a pé)"),
    ("sem_mercado", lambda f: f["dist_mercado_m"] >= NAO_ENCONTRADO, -15,
     "SE não há mercado por perto ENTÃO -15 (sem estoque de comida)"),

    ("farmacia_perto", lambda f: f["dist_farmacia_m"] <= 800, +10,
     "SE há farmácia a até 800 m ENTÃO +10 (remédios e curativos)"),
    ("sem_farmacia", lambda f: f["dist_farmacia_m"] >= NAO_ENCONTRADO, -10,
     "SE não há farmácia por perto ENTÃO -10 (sem suprimentos médicos)"),

    ("hospital_perto", lambda f: f["dist_hospital_m"] <= 1500, +10,
     "SE há hospital a até 1,5 km ENTÃO +10 (atendimento próximo)"),
    ("hospital_perigo", lambda f: f["dist_hospital_m"] <= 1500, -5,
     "SE há hospital a até 1,5 km ENTÃO -5 (hospitais são os primeiros focos de infecção)"),

    ("posto_perto", lambda f: f["dist_posto_m"] <= 1000, +8,
     "SE há posto de combustível a até 1 km ENTÃO +8 (fuga de carro)"),

    ("chuva_forte", lambda f: f["chuva_mm"] >= 2.0, -10,
     "SE está chovendo forte ENTÃO -10 (visibilidade e ruído atrapalham a fuga)"),
    ("frio", lambda f: f["temperatura_c"] <= 10, -8,
     "SE faz 10 °C ou menos ENTÃO -8 (hipotermia)"),
    ("calor", lambda f: f["temperatura_c"] >= 35, -8,
     "SE faz 35 °C ou mais ENTÃO -8 (desidratação)"),
    ("clima_bom", lambda f: 15 <= f["temperatura_c"] <= 28 and f["chuva_mm"] < 0.5, +7,
     "SE o clima está ameno e seco ENTÃO +7 (boas condições para se deslocar)"),
]

CAMPOS = ["dist_mercado_m", "dist_farmacia_m", "dist_hospital_m",
          "dist_posto_m", "chuva_mm", "temperatura_c"]


def avaliar(fatos: dict) -> dict:
    """Aplica todas as regras aos fatos e devolve pontuação, veredito e regras disparadas."""
    faltando = [c for c in CAMPOS if c not in fatos]
    if faltando:
        raise ValueError(f"Fatos faltando: {faltando}")

    pontos = PONTUACAO_BASE
    disparadas = []
    for nome, condicao, delta, explicacao in REGRAS:
        if condicao(fatos):
            pontos += delta
            disparadas.append({"regra": nome, "pontos": delta, "explicacao": explicacao})

    chance = max(0, min(100, pontos))
    return {"chance": chance, "veredito": _veredito(chance), "regras_disparadas": disparadas}


def _veredito(chance: int) -> str:
    if chance >= 75:
        return "Você sobrevive (com estilo)"
    if chance >= 50:
        return "Sobrevive, mas com sustos"
    if chance >= 30:
        return "Situação crítica"
    return "Você vira lanche de zumbi"
