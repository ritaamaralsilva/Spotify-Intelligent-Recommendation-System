import os
import urllib.parse
from security import create_session_token, verify_session_token
from fastapi import FastAPI, HTTPException, Response, Cookie, Depends
from fastapi.responses import RedirectResponse
import httpx
from fastapi.middleware.cors import CORSMiddleware
from src.spotify_client import SpotifyExtractor
from src.ai_recommender import AIRecommender
from dotenv import load_dotenv

from database import engine, Base  
import models  # Garante que o ficheiro com as classes (User, etc.) é lido

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

app = FastAPI(title="Spotify Recommendation System API", version="1.0")

Base.metadata.create_all(bind=engine)

# --- CENTRALIZAÇÃO DE URLS E CONFIGURAÇÕES DE AMBIENTE ---
FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPES = "user-library-read playlist-read-private playlist-modify-public playlist-modify-private"

# Configuração de segurança CORS para permitir chamadas do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa os módulos de extração e recomendação
extractor = SpotifyExtractor() 
recommender = AIRecommender() 

# Dependencia de validacao do token de sessão
def get_current_token(session_token: str = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada. Faz login novamente.")
    
    spotify_token = verify_session_token(session_token)
    if not spotify_token:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return spotify_token

# Rotas de autenticação e recomendação (OAUTH2 + Cookie)

@app.get("/api/login")
def spotify_login():
    """Rota que redireciona o usuário para a página de login do Spotify"""
    payload = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES,
        "show_dialog": "false"
    }
    url_args = urllib.parse.urlencode(payload)
    return RedirectResponse(f"https://accounts.spotify.com/authorize?{url_args}")

@app.get("/api/callback")
async def spotify_callback(response: Response, code: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Erro de autenticação do Spotify: {error}")
    """Rota que recebe o callback do Spotify e cria o token de sessão"""
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização em falta.")
    
    # Troca o código de autorização pelo token de acesso
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Falha ao obter token do Spotify.")
    
    spotify_token = token_response.json().get("access_token")
    meu_jwt_seguro = create_session_token(spotify_token)

    redirect = RedirectResponse(url=f"{FRONTEND_URL}/")
    
    redirect.set_cookie(
        key="session_token",
        value=meu_jwt_seguro,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600,  # 1 hora
        path="/"
    )
    return redirect

# Rotas protegidas da aplicação (necessitam de token de sessão válido)
@app.get("/api/scan")
def scan_spotify(spotify_token: str = Depends(get_current_token)):
    """Rota que consome o api do Spotify para procurar as bibliotecas do user e cria o dataset local .txt"""
    try:
        artistas = extractor.extrair_todos_os_artistas(token=spotify_token)
        extractor.salvar_dataset(artistas)
        return {"status": "success", "total_artistas": len(artistas)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/recommend")
def get_recommendations(spotify_token: str = Depends(get_current_token)):
    """Rota que chama a api do OpenAI e filtra as repetições"""
    try:
        descobertas = recommender.obter_recomendacoes()
        return {"status": "success", "recommendations": descobertas}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Corre o servidor do Python
    port_split = BACKEND_URL.split(":")[-1].replace("/", "")
    port = int(port_split) if port_split.isdigit() else 8000

    uvicorn.run(app, host="127.0.0.1", port=port)
    