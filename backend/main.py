import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "False") == "True"

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


from database import engine, Base, get_db
import models  


app = FastAPI(title="Spotify Recommendation System API", version="1.0")

Base.metadata.create_all(bind=engine)

# --- CENTRALIZAÇÃO DE URLS E CONFIGURAÇÕES DE AMBIENTE ---
FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPES = "user-library-read playlist-read-private playlist-modify-public playlist-modify-private"

# Em produção (frontend e backend em domínios diferentes) o cookie tem de ser
# SameSite=None + Secure=True para o browser aceitar enviá-lo entre domínios.
# Em desenvolvimento local (mesmo host, portas diferentes) isso quebraria o cookie,
# porque Secure exige HTTPS. Por isso alternamos consoante o ambiente.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
COOKIE_SECURE = ENVIRONMENT == "production"
COOKIE_SAMESITE = "none" if ENVIRONMENT == "production" else "lax"

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
        secure=COOKIE_SECURE,  # True em produção, False em desenvolvimento
        samesite=COOKIE_SAMESITE, 
        max_age=3600,  # 1 hora
        path="/"
    )
    return redirect

# Rotas protegidas da aplicação (necessitam de token de sessão válido)
@app.get("/api/scan")
def scan_spotify(
    spotify_token: str = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Rota que consome a api do Spotify para procurar as bibliotecas do user, cria o dataset local .txt
    e grava/atualiza os artistas (com géneros) e a relação user-artista na base de dados MySQL."""
    try:
        # descobre o ID do utilizador atual no Spotify
        with httpx.Client() as client:
            me_res = client.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {spotify_token}"}
            )
            if me_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Não foi possível obter dados do Spotify.")
            spotify_user_id = me_res.json()["id"]

        artistas_nomes = extractor.extrair_todos_os_artistas(token=spotify_token)
        extractor.salvar_dataset(artistas_nomes)

        # garante que o utilizador existe na tabela users
        user_db = db.query(models.User).filter(models.User.spotify_id == spotify_user_id).first()
        if not user_db:
            user_db = models.User(spotify_id=spotify_user_id)
            db.add(user_db)
            db.commit()

        # grava/atualiza cada artista e a sua relação com o utilizador
        for nome_artista in artistas_nomes:
            artist_db = db.query(models.Artist).filter(models.Artist.name == nome_artista).first()

            if not artist_db:
                artist_db = models.Artist(name=nome_artista, genres=None)  # inicialmente sem géneros (terei de recorrer a outra API para ir buscar essa info se quiser complementar no futuro)
                db.add(artist_db)
                db.commit()

            relacao_existente = (
                db.query(models.UserArtist)
                .filter(
                    models.UserArtist.spotify_id == spotify_user_id,
                    models.UserArtist.artist_id == artist_db.id
                )
                .first()
            )
            if not relacao_existente:
                db.add(models.UserArtist(spotify_id=spotify_user_id, artist_id=artist_db.id))
                db.commit()

        return {"status": "success", "total_artistas": len(artistas_nomes)}
    except Exception as e:
        db.rollback()
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
    except HTTPException:
        # deixa passar HTTPException tal como foi lançada (400, 401, etc.),
        # sem a envolver num 500 genérico
        db.rollback()
        raise
    except Exception as e:
        db.rollback()  # desfaz alterações na BD em caso de erro
        raise HTTPException(status_code=500, detail=f"Erro ao gerar a playlist: {str(e)}")
    
# rota para obter estatísticas de géneros (Top 5 artistas mais proeminentes na biblioteca do user)
@app.get("/api/stats/genres")
def get_genre_stats(
    spotify_token: str = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Adaptado: Devolve o Top 5 de Artistas mais proeminentes na biblioteca do user."""
    try:
        with httpx.Client() as client:
            me_res = client.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {spotify_token}"})
            if me_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Não foi possível obter dados do Spotify.")
            spotify_user_id = me_res.json()["id"]

        # Procura os nomes dos artistas associados a este utilizador
        artistas_db = (
            db.query(models.Artist.name)
            .join(models.UserArtist, models.Artist.id == models.UserArtist.artist_id)
            .filter(models.UserArtist.spotify_id == spotify_user_id)
            .limit(5) # Pegamos em 5 para simular o Top 5
            .all()
        )

        if not artistas_db:
            return {"status": "success", "top_genres": []}

        
        # Formata os dados para o frontend (React) sem alterar a lógica do código existente
        top_artistas_formatado = [
            {
                "genre": row.name, # Passa o nome do artista no lugar do género para o React ler sem alterar o código
                "count": 1,
                "percentage": round((1 / len(artistas_db)) * 100, 1)
            }
            for row in artistas_db
        ]

        return {
            "status": "success",
            "total_tags_analisadas": len(artistas_db),
            "top_genres": top_artistas_formatado
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estatísticas: {str(e)}")

# rota antiga para compatibilidade com o frontend legado (depreciada)
@app.get("/api/recommend")
def get_recommendations():
    """Rota legada. O frontend deve usar a nova rota POST /api/recommend/generate-playlist"""
    return {
        "status": "deprecated", 
        "message": "Usa a nova rota POST /api/recommend/generate-playlist para criar playlists customizadas."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)