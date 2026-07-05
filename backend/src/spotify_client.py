import os
import time
import spotipy

class SpotifyExtractor:
    def __init__(self):
        # O cliente é criado de forma dinâmica com o token de user que fizer o pedido
        pass

    def extrair_todos_os_artistas(self, token: str):
        """Recebe o token do user atual extraído do Cookie JWT, percorre Músicas Apreciadas e Playlists,
        e devolve um conjunto (set) com os nomes de todos os artistas únicos encontrados.
        Aplica um rate limiter com time.sleep para segurança."""

        sp = spotipy.Spotify(auth=token)
        artistas_conhecidos = set()  # set para armazenar nomes de artistas únicos

        # Tetos para proteger contra rate limits do Spotify
        MAX_MUSICAS_APRECIADAS = 1000
        MAX_PLAYLISTS = 50
        MAX_MUSICAS_POR_PLAYLIST = 1000

        # extrair de Músicas Apreciadas
        try:
            print("A aceder às Músicas de que gostaste...")
            offset = 0

            while offset < MAX_MUSICAS_APRECIADAS:
                results = sp.current_user_saved_tracks(limit=50, offset=offset)

                if not results or 'items' not in results or len(results['items']) == 0:
                    break  # Acabaram as músicas apreciadas

                for item in results['items']:
                    if item and 'track' in item and item['track']:
                        if 'artists' in item['track'] and item['track']['artists']:
                            for artista in item['track']['artists']:
                                if artista.get('name'):
                                    artistas_conhecidos.add(artista['name'])
                                    
                offset += 50
                time.sleep(0.5)  # Pausa de segurança

        except Exception as e:
            print(f"Aviso ao ler Músicas Apreciadas: {e}")

        # extrair de Playlists do user
        print("A aceder às tuas Playlists...")
        try:
            playlists = sp.current_user_playlists(limit=MAX_PLAYLISTS)
            if playlists and 'items' in playlists:
                for playlist in playlists['items']:
                    try:
                        playlist_id = playlist['id']
                        offset_playlist = 0

                        while offset_playlist < MAX_MUSICAS_POR_PLAYLIST:
                            playlist_tracks = sp.playlist_items(playlist_id, limit=50, offset=offset_playlist)
                            if not playlist_tracks or 'items' not in playlist_tracks or len(playlist_tracks['items']) == 0:
                                break  # Fim da playlist

                            for item in playlist_tracks['items']:
                                if item and 'track' in item and item['track']:
                                    if 'artists' in item['track'] and item['track']['artists']:
                                        for artista in item['track']['artists']:
                                            if artista.get('name'):
                                                artistas_conhecidos.add(artista['name'])

                            offset_playlist += 50
                            time.sleep(0.5)

                        time.sleep(1)  # Pausa extra entre playlists

                    except Exception:
                        print(f"Ignorada a playlist '{playlist['name']}' devido a restrições de acesso.")
                        continue

        except Exception as e:
            print(f"Erro geral nas playlists: {e}")

        # retorna o conjunto de artistas únicos encontrados
        return artistas_conhecidos

    def salvar_dataset(self, artistas, caminho_arquivo="data/historico_artistas.txt"):
        """Guarda o dataset local em .txt ordenado alfabeticamente."""
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            for artista in sorted(artistas):
                f.write(f"{artista}\n")
        print(f"Dataset guardado com sucesso! Mapeados {len(artistas)} artistas.")