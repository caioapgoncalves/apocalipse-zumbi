# 🧟 Plano Anti-Apocalipse Zumbi

O usuário digita um bairro e cidade. O Gemini, usando **function calling**, pede ao nosso back-end
dados reais de mapa e clima (**APIs externas**); um **sistema especialista** calcula a chance de
sobrevivência com regras explicáveis; e o "Sargento Sobrevivência" escreve o plano com humor.

## Como rodar no Windows (passo a passo)

1. Extraia o zip numa pasta **nova** (ex.: Área de Trabalho). Abra a pasta `plano-zumbi` no VS Code
   (**Arquivo → Abrir Pasta**) e abra o terminal (**Terminal → Novo Terminal**).
2. Crie e ative o ambiente virtual:
   ```
   py -m venv venv
   venv\Scripts\activate
   ```
   (Se o PowerShell bloquear: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e repita.)
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Crie o `.env` e cole a sua chave (https://aistudio.google.com/apikey):
   ```
   copy .env.example .env
   notepad .env
   ```
5. **Rode o diagnóstico** (testa chave, Gemini, mapa e clima, um por um):
   ```
   python diagnostico.py
   ```
   Se algo falhar, ele diz o quê. Se o problema for o modelo, ele mostra qual colocar no `.env`.
6. Com o diagnóstico OK, suba o servidor:
   ```
   uvicorn app.main:app --reload
   ```
7. Abra http://localhost:8000. A documentação da API fica em http://localhost:8000/docs.

> O `.env` está no `.gitignore`. Nunca coloque a chave no `.env.example` nem no código.

## Arquitetura em camadas

Cada camada só conversa com a de baixo.

```
frontend/index.html                     → Interface
        │  POST /plano {"local": "..."}
        ▼
app/api/rotas.py                        → API: HTTP e tradução de erros (500/502)
        │   app/schemas/plano.py        → validação da entrada e formato da saída
        ▼
app/services/plano_service.py           → Serviço: caso de uso "gerar plano"
app/services/agente_service.py          → Serviço: loop de function calling
app/services/ferramentas.py             → Serviço: declarações + execução das funções
        ▼
app/clients/                            → Infraestrutura (mundo externo)
   ├─ gemini_client.py   → Gemini (SDK google-genai)
   ├─ mapa_client.py     → Nominatim + Overpass (OpenStreetMap)
   └─ clima_client.py    → Open-Meteo
app/domain/                             → Domínio (regras puras, sem HTTP e sem IA)
   ├─ regras.py          → sistema especialista
   └─ geo.py             → distância (Haversine)
app/core/                               → Configuração (.env) e erros próprios
```

### Como funciona o function calling (`agente_service.py`)

```
1. Enviamos ao Gemini: pergunta + "cardápio" de funções (DECLARACOES)
2. Gemini responde: "quero geocodificar('Centro, Araraquara')"
3. NOSSO código executa e devolve o resultado ao Gemini
4. Gemini: "quero buscar_locais_proximos(...) e ver_clima(...)"   ← pode pedir duas juntas
5. NOSSO código executa as duas e devolve
6. Gemini: "quero calcular_chance_sobrevivencia(...)"
7. NOSSO código executa (sistema especialista) e devolve
8. Gemini escreve o plano final em texto → fim do loop
```

O terminal mostra cada etapa:
```
[gemini] etapa 1: respondeu em 2.1s
[function calling] geocodificar({'local': 'Centro, Araraquara'}) -> ok (0.8s)
...
```

## Onde mexer para…

| Quero… | Arquivo |
|---|---|
| mudar/adicionar uma regra de sobrevivência | `app/domain/regras.py` |
| mudar a personalidade do Sargento | `app/services/plano_service.py` (`INSTRUCOES`) |
| adicionar uma função para o Gemini | `app/services/ferramentas.py` (declaração + implementação) |
| trocar a API de clima ou mapa | `app/clients/` |
| trocar o modelo do Gemini | `.env` (`MODELO_GEMINI=...`) |
| mudar raio, timeouts, limite de etapas | `app/core/config.py` |
| mudar a validação da entrada | `app/schemas/plano.py` |
| mudar a tela | `frontend/index.html` |

## Perguntas que o professor pode fazer (todos devem saber responder)

**Por que arquitetura em camadas?**
Separa responsabilidades: a API não sabe de regra de negócio, o domínio não sabe de HTTP nem de IA,
e os clients isolam as APIs externas. Trocar uma peça mexe em um lugar só.

**O que é function calling?**
Enviamos ao modelo uma lista de funções (nome, descrição, parâmetros). Em vez de responder direto,
ele pode devolver um pedido: "execute esta função com estes argumentos". O nosso back-end executa,
devolve o resultado, e o modelo continua até escrever a resposta final. **O modelo nunca executa nada sozinho.**

**Onde isso está no código?**
`ferramentas.py` (o cardápio `DECLARACOES` e o `executar`) e `agente_service.py` (o loop).
Fizemos o loop manualmente, em vez do modo automático do SDK, para cada etapa ficar visível.

**Por que precisamos de function calling aqui?**
O Gemini não sabe onde ficam os mercados do bairro nem o clima de agora. Sem as funções, ele inventaria.

**Quem decide a ordem das chamadas?**
O Gemini, guiado pelas instruções (`INSTRUCOES`) e pelas descrições das funções.

**Por que a chance não é calculada pelo Gemini?**
Modelos de linguagem erram contas e variam a resposta. As regras em `regras.py` dão sempre o mesmo
resultado e explicam o porquê (explicabilidade, característica de sistemas especialistas).

**O que é o sistema especialista aqui?**
Base de conhecimento (a lista `REGRAS`), motor de inferência (`avaliar`) e explicação
(as regras disparadas aparecem na tela).

**Quais APIs externas?**
Nominatim (endereço → coordenadas), Overpass (locais próximos) e Open-Meteo (clima). São gratuitas e sem chave.

**Onde fica a chave do Gemini?**
No `.env`, lida só pelo back-end (`core/config.py`). No front-end, qualquer um poderia roubá-la.

**E se uma API externa cair?**
O client lança `ErroServicoExterno`; `ferramentas.executar` transforma em `{"erro": ...}`; o Gemini
recebe isso e explica ao usuário. O Overpass ainda tem 3 servidores de reserva.

**E se o Gemini entrar em loop pedindo funções?**
O loop tem limite de etapas (`MAX_ETAPAS_FUNCTION_CALLING`), e a API responde 502.

**Que validações existem?**
Local com 3 a 100 caracteres (Pydantic), chave configurada, função existente, argumentos completos,
local encontrado e fatos completos no sistema especialista.

## Roteiro da apresentação

1. Problema e ideia (30 s).
2. Arquitetura em camadas (diagrama acima).
3. Demo: bairro de alguém da sala; abrir "Por quê?" e "Funções que o Gemini pediu"; mostrar o terminal.
4. Código: `ferramentas.py` (cardápio), `agente_service.py` (loop) e uma regra em `regras.py`.
