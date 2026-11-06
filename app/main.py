"""Ponto de entrada: cria o app FastAPI, liga as rotas e serve o front-end."""
from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.rotas import router
from app.core import config

app = FastAPI(title="Plano Anti-Apocalipse Zumbi")
# Sem CORS de propósito: o front-end é servido por este mesmo app (mesma origem),
# então nenhum outro site consegue chamar a API pelo navegador do usuário.
app.include_router(router)


@app.get("/", include_in_schema=False)
def pagina():
    return FileResponse(config.ARQUIVO_FRONTEND)
