#!/bin/bash
# Instalar dependências da pasta backend
pip install -r backend/requirements.txt

# Iniciar o servidor
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app