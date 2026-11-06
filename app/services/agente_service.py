"""Camada de serviço — o loop de function calling (o "coração" do projeto).

1. Manda a pergunta + a lista de funções para o Gemini.
2. Se o Gemini pedir funções, o NOSSO código executa cada uma.
3. Devolve os resultados ao Gemini.
4. Repete até o Gemini responder com texto (ou atingir o limite de etapas).
"""
import time

from google.genai import types

from app.clients import gemini_client
from app.core import config
from app.core.excecoes import ErroIA
from app.services import ferramentas


def executar_agente(instrucoes: str, mensagem: str, log: list) -> str:
    conversa = [types.Content(role="user", parts=[types.Part.from_text(text=mensagem)])]

    for etapa in range(1, config.MAX_ETAPAS_FUNCTION_CALLING + 1):
        inicio = time.perf_counter()
        resposta = gemini_client.gerar(conversa, instrucoes, ferramentas.DECLARACOES)
        print(f"[gemini] etapa {etapa}: respondeu em {time.perf_counter() - inicio:.1f}s", flush=True)

        pedidos = resposta.function_calls or []
        if not pedidos:
            return (resposta.text or "").strip() or "O Sargento ficou sem palavras. Tente de novo."

        # Guarda a mensagem do modelo (com os pedidos) no histórico da conversa.
        conversa.append(resposta.candidates[0].content)

        respostas_funcoes = []
        for pedido in pedidos:
            argumentos = dict(pedido.args or {})
            inicio = time.perf_counter()
            resultado = ferramentas.executar(pedido.name, argumentos)
            segundos = round(time.perf_counter() - inicio, 1)

            status = "ERRO: " + resultado["erro"] if "erro" in resultado else "ok"
            print(f"[function calling] {pedido.name}({argumentos}) -> {status} ({segundos}s)", flush=True)
            log.append({"ferramenta": pedido.name, "argumentos": argumentos,
                        "resultado": resultado, "segundos": segundos})

            respostas_funcoes.append(types.Part(function_response=types.FunctionResponse(
                id=pedido.id, name=pedido.name, response={"resultado": resultado})))

        conversa.append(types.Content(role="user", parts=respostas_funcoes))

    raise ErroIA("O Gemini passou do limite de etapas sem terminar o plano.")
