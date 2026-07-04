import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

class SpotifyExtractor:
    def __init__(self):
        scope = "user-library-read playlist-read-private playlist-read-collaborative"
        
        # Criamos o gerenciador de autenticação explicitamente
        self.auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope=scope,
            open_browser=True
        )
        
        # FORÇAR LIMPEZA DE CACHE INTERNA
        # Isto obriga o Spotipy a esquecer qualquer token antigo guardado
        self.auth_manager.cache_handler.save_token_to_cache({})
        
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)

    def extrair_todos_os_artistas(self):
        """Varre as músicas curtidas e as playlists para recolher os artistas com segurança máxima."""
        artistas_conhecidos = set()

        # 1. Extrair de "Músicas Curtidas"
        try:
            print("A aceder às Músicas Curtidas...")
            results = self.sp.current_user_saved_tracks(limit=50)
            while results:
                for item in results['items']:
                    if item and 'track' in item and item['track']:
                        if 'artists' in item['track'] and item['track']['artists']:
                            for artista in item['track']['artists']:
                                artistas_conhecidos.add(artista['name'])
                results = self.sp.next(results) if results['next'] else None
        except Exception as e:
            print(f"Aviso ao ler Músicas Curtidas: {e}")

        # 2. Extrair de todas as Playlists
        print("A aceder às tuas Playlists...")
        try:
            playlists = self.sp.current_user_playlists()
            while playlists:
                for playlist in playlists['items']:
                    # CORREÇÃO CRÍTICA: Envolver a leitura de CADA playlist num bloco try/except
                    try:
                        playlist_tracks = self.sp.playlist_tracks(playlist['id'])
                        while playlist_tracks:
                            for item in playlist_tracks['items']:
                                if item and 'track' in item and item['track']:
                                    if 'artists' in item['track'] and item['track']['artists']:
                                        for artista in item['track']['artists']:
                                            artistas_conhecidos.add(artista['name'])
                            playlist_tracks = self.sp.next(playlist_tracks) if playlist_tracks['next'] else None
                    except Exception as e_playlist:
                        # Se uma playlist específica der 403 (Forbidden), o programa avisa no terminal, 
                        # ignora-a e continua a ler as outras em vez de crashar!
                        print(f"Ignorada a playlist '{playlist['name']}' devido a restrições de acesso (403).")
                        continue
                
                playlists = self.sp.next(playlists) if playlists['next'] else None
        except Exception as e:
            print(f"Erro geral nas playlists: {e}")

        return artistas_conhecidos

    def salvar_dataset(self, artistas, caminho_arquivo="data/historico_artistas.txt"):
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            for artista in sorted(artistas):
                f.write(f"{artista}\n")
        print(f"Dataset guardado com sucesso! Mapeados {len(artistas)} artistas.")