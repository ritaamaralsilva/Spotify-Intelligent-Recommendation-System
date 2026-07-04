import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.spotify_client import SpotifyExtractor
from src.ai_recommender import AIRecommender

app = FastAPI(title="SpotiFinder AI API")

# Configuração de CORS para permitir que o teu React (porta 5173) comunique com o Python (porta 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em desenvolvimento local usamos "*" por simplicidade
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa os dois módulos que criámos
extractor = SpotifyExtractor()
recommender = AIRecommender()

@app.get("/api/scan")
def scan_spotify():
    """Rota que varre o teu Spotify e cria o dataset local .txt"""
    try:
        artistas = extractor.extrair_todos_os_artistas()
        extractor.salvar_dataset(artistas)
        return {"status": "success", "total_artistas": len(artistas)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/recommend")
def get_recommendations():
    """Rota que chama a OpenAI e filtra as repetições"""
    try:
        descobertas = recommender.obter_recomendacoes()
        return {"status": "success", "recommendations": descobertas}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Corre o servidor local do Python na porta 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
    