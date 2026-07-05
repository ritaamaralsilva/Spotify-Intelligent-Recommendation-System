import os
import urllib.parse
from security import create_session_token, verify_session_token
from fastapi import FastAPI, HTTPException, Response, Cookie, Depends
from fastapi.responses import RedirectResponse
import httpx
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.spotify_client import SpotifyExtractor
from src.ai_recommender import AIRecommender
from src.spotify_playlister import SpotifyPlaylister
from dotenv import load_dotenv

from database import engine, Base, get_db
import models  

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
playlister = SpotifyPlaylister()

# Dependencia de validacao do token de sessão
def get_current_token(session_token: str = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada. Faz login novamente.")
    
    spotify_token = verify_session_token(session_token)
    if not spotify_token:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return spotify_token

#schema para receber o nome da playlist do frontend (user input)
class PlaylistRequest(BaseModel):
    playlist_name: str

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
        secure=False, #mudar para True em produção com HTTPS
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
    
# rota para gerar a playlist com as recomendações
@app.post("/api/recommend/generate-playlist")
async def generate_ai_playlist(
    dados_request: PlaylistRequest,
    spotify_token: str = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Gera 10 artistas emergentes recomendados e cria uma playlist no Spotify com as suas 5 melhores faixas cada (até 50 faixas no total)"""
    try: 
        # descobre quem é o utilizador atual perguntando ao spotify
        spotify_user_id = await playlister.obter_user_id(spotify_token)
        
        # chamar a IA passando a sessão da BD e o ID do utilizador (Usa a lógica dos géneros do MySQL)
        artistas_descobertos = recommender.obter_recomendacoes(db, spotify_user_id)

        if not artistas_descobertos:
            raise HTTPException(
                status_code=400,
                detail="Não foram encontradas recomendações. Certifica-te de que já fizeste o scan da tua conta do Spotify."
            )
        
        # criar uma playlist vazia no Spotify com o nome fornecido pelo user
        playlist_id, playlist_url = await playlister.criar_playlist_vazia(
            token=spotify_token,
            spotify_user_id=spotify_user_id,
            nome_playlist=dados_request.playlist_name
        )
        
        # preencher a playlist com as faixas dos artistas recomendados (até 50 faixas no total)
        total_musicas = await playlister.preencher_playlist(
            token=spotify_token,
            playlist_id=playlist_id,
            artistas_sugeridos=artistas_descobertos
        )
        
        # guardar a playlist gerada na base de dados para histórico do user
        nova_playlist_db = models.GeneratedPlaylist(
            spotify_id=spotify_user_id,
            playlist_spotify_id=playlist_id,
            name=dados_request.playlist_name,
            url=playlist_url
        )
        db.add(nova_playlist_db)
        db.commit()

        return {
            "status": "success",
            "message": f"Playlist '{dados_request.playlist_name}' criada com sucesso!",
            "playlist_url": playlist_url,
            "tracks_count": total_musicas,
            "artists_discovered": artistas_descobertos
        }
    except Exception as e:
        db.rollback()  # desfaz alterações na BD em caso de erro
        raise HTTPException(status_code=500, detail=f"Erro ao gerar a playlist: {str(e)}")

# rota antiga para compatibilidade com o frontend legado (depreciada)
@app.get("/api/recommend")
def get_recommendations():
    """Rota legada. O frontend deve usar a nova rota POST /api/recommend/generate-playlist"""
    return {
        "status": "deprecated", 
        "message": "Usa a nova rota POST /api/recommend/generate-playlist para criar playlists customizadas."
    }
    