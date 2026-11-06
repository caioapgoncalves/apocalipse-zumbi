"""Diagnóstico: testa cada peça do projeto separadamente.

Rode na pasta do projeto, com o venv ativado:
    python diagnostico.py
"""
import time

from app.clients import clima_client, gemini_client, mapa_client
from app.core import config

LAT, LON = -21.7946, -48.1756  # Centro de Araraquara (usado se o endereço falhar)
ok_geral = True


def etapa(titulo, funcao, critica=True):
    global ok_geral
    print(f"\n>> {titulo}", flush=True)
    inicio = time.perf_counter()
    try:
        resultado = funcao()
        print(f"   OK ({time.perf_counter() - inicio:.1f}s): {resultado}", flush=True)
        return resultado
    except Exception as e:
        if critica:
            ok_geral = False
        print(f"   FALHOU ({time.perf_counter() - inicio:.1f}s): {e}", flush=True)
        return None


print("=" * 60)
print("DIAGNÓSTICO - Plano Anti-Apocalipse Zumbi")
print("=" * 60)

# 1. Chave
chave = config.GOOGLE_API_KEY
print("\n>> Arquivo .env")
if not chave or chave == "cole_sua_chave_aqui":
    print(f"   FALHOU: chave não encontrada em {config.RAIZ / '.env'}")
    raise SystemExit(1)
print(f"   OK: chave lida ({chave[:6]}...{chave[-4:]}), modelo = {config.MODELO_GEMINI}")

# 2. Gemini
print("\n(cada teste do Gemini desiste em 20 s)")
resposta = etapa(f"Gemini com o modelo do .env ({config.MODELO_GEMINI})",
                 lambda: gemini_client.testar_modelo(config.MODELO_GEMINI))

if resposta is None:
    modelos = etapa("Buscando modelos 'flash' disponíveis para a sua chave",
                    gemini_client.listar_modelos_flash, critica=False) or []
    funcionando = []
    for modelo in modelos[:6]:
        inicio = time.perf_counter()
        if etapa(f"Testando {modelo}", lambda m=modelo: gemini_client.testar_modelo(m), critica=False):
            funcionando.append((time.perf_counter() - inicio, modelo))
    if funcionando:
        melhor = min(funcionando)[1]
        print("\n" + "!" * 60)
        print(f"   SOLUÇÃO: abra o .env e troque a linha do modelo por:")
        print(f"   MODELO_GEMINI={melhor}")
        print("   Depois rode este diagnóstico de novo.")
        print("!" * 60)
    else:
        print("\n   Nenhum modelo respondeu. Verifique a internet e se a chave é do AI Studio")
        print("   (https://aistudio.google.com/apikey).")

# 3. APIs externas
geo = etapa("Endereço (Nominatim)", lambda: mapa_client.geocodificar("Centro, Araraquara"))
lat, lon = (geo["latitude"], geo["longitude"]) if geo else (LAT, LON)


def contar_locais():
    pontos = mapa_client.buscar_pontos(lat, lon)
    return {t: sum(p["tipo"] == t for p in pontos) for t in mapa_client.TIPOS}


etapa("Locais próximos (Overpass)", contar_locais)
etapa("Clima (Open-Meteo)", lambda: clima_client.clima_atual(lat, lon))

# 4. Fluxo completo
if ok_geral:
    from app.services.plano_service import gerar_plano
    plano = etapa("Fluxo completo com function calling", lambda: gerar_plano("Centro, Araraquara"))
    if plano:
        print(f"\n   Chance: {plano.chance}% | Funções: {[f.ferramenta for f in plano.ferramentas_usadas]}")
        print(f"\n{plano.plano}")

print("\n" + "=" * 60)
print("TUDO CERTO! Rode: uvicorn app.main:app --reload" if ok_geral
      else "Algo falhou. Siga a SOLUÇÃO acima (se houver) ou mande o print desta tela.")
print("=" * 60)