import os
import time
import spotipy

class SpotifyExtractor:
    def __init__(self):
        # o cliente é criado de forma dinâmica com o token de user que fizer o pedido 
        pass

    def extrair_todos_os_artistas(self, token: str):
        """Recebe o token do user atual extraído do Cookie JWT e aplica um rate limiter para a api do spotify não bloquear o pedido"""

        sp = spotipy.Spotify(auth=token)
        artistas_conhecidos = set()

        #tetos para proteger contra rate limits do Spotify
        MAX_MUSICAS_APRECIADAS = 1000
        MAX_PLAYLISTS = 30
        MAX_MUSICAS_POR_PLAYLIST = 500


        # 1. Extrair de "Músicas Apreciadas" com paginação (limit=1000)
        try:
            print("A aceder às Músicas de que gostaste...")
            offset = 0

            while (offset < MAX_MUSICAS_APRECIADAS):
                #o spotify permite no máximo 50 músicas por pedido, então fazemos paginação
                results = sp.current_user_saved_tracks(limit=50, offset=offset)

                if not results or 'items' not in results or len(results['items']) == 0:
                    break #acabaram as músicas apreciadas, ciclo acaba aqui
            
                for item in results['items']:
                    if item and 'track' in item and item['track']:
                        if 'artists' in item['track'] and item['track']['artists']:
                            for artista in item['track']['artists']: # for each artist in the track
                                artistas_conhecidos.add(artista['name']) #adiciona o nome do artista ao set de artistas conhecidos
                #avança para a próxima página de músicas apreciadas                
                offset += 50
                #pausa de 0.5 segundos para não sobrecarregar a API do Spotify (e não causar rate limit)
                time.sleep(0.5)

        except Exception as e:
            print(f"Aviso ao ler Músicas Apreciadas: {e}")

        # 2. Extrair de todas as Playlists do user com paginação (limit=30 playlists, 500 músicas por playlist)
        print("A aceder às tuas Playlists...")
        try:
            playlists = self.sp.current_user_playlists(limit=MAX_PLAYLISTS)
            if playlists and 'items' in playlists:
                for playlist in playlists['items']:

                    # Envolver a leitura de cada playlist num bloco try/except
                    try:
                        playlist_id = playlist['id']
                        offset_playlist = 0

                        while offset_playlist < MAX_MUSICAS_POR_PLAYLIST:
                            playlist_tracks = self.sp.playlist_items(playlist_id, limit=50, offset=offset_playlist)
                            if not playlist_tracks or 'items' not in playlist_tracks or len(playlist_tracks['items']) == 0:
                                break #acabaram as músicas na playlist, ciclo acaba aqui

                            for item in playlist_tracks['items']:
                                if item and 'track' in item and item['track']:
                                    if 'artists' in item['track'] and item['track']['artists']:
                                        for artista in item['track']['artists']:
                                            artistas_conhecidos.add(artista['name'])

                            offset_playlist += 50
                            time.sleep(0.5)  # Pausa para evitar rate limit

                        #pausa extra depois de cada playlist para evitar rate limit
                        time.sleep(1)

                           
                    except Exception as e_playlist:
                        # Se uma playlist específica der 403 (Forbidden), o programa avisa no terminal, 
                        # ignora-a e continua a ler as outras em vez de crashar o programa inteiro.
                        print(f"Ignorada a playlist '{playlist['name']}' devido a restrições de acesso.")
                        continue #continua a procurar nas outras playlists
                
                
        except Exception as e:
            print(f"Erro geral nas playlists: {e}")

        return artistas_conhecidos

    def salvar_dataset(self, artistas, caminho_arquivo="data/historico_artistas.txt"):
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            for artista in sorted(artistas):
                f.write(f"{artista}\n")
        print(f"Dataset guardado com sucesso! Mapeados {len(artistas)} artistas.")