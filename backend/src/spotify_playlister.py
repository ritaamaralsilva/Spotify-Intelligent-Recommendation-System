import httpx
import asyncio

class SpotifyPlaylister:
    def __init__(self):
        self.base_url = "https://api.spotify.com/v1"

    async def obter_user_id(self, token: str) -> str:
        """Procura o ID do utilizador dono do token do Spotify."""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/me", headers=headers)
            if res.status_code != 200:
                raise Exception("Não foi possível obter o perfil do utilizador no Spotify.")
            return res.json()["id"]

    async def criar_playlist_vazia(self, token: str, spotify_user_id: str, nome_playlist: str) -> tuple:
        """Cria uma playlist vazia e privada na conta do utilizador."""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "name": nome_playlist,
            "description": "Gerada por Spotify Intelligent Recommendation System - Descobertas emergentes fora do radar.",
            "public": False
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/users/{spotify_user_id}/playlists", 
                json=payload, 
                headers=headers
            )
            if res.status_code != 201:
                raise Exception(f"Erro ao criar playlist: {res.text}")
            dados = res.json()
            return dados["id"], dados["external_urls"]["spotify"]

    async def buscar_top_tracks_por_artista(self, client: httpx.AsyncClient, headers: dict, nome_artista: str) -> list:
        """Pesquisa um artista e extrai as suas 5 melhores faixas."""
        uris_artista = []
        try:
            # pesquisa o artista pelo nome (limit=1 para apanhar o mais relevante)
            url_search = f"{self.base_url}/search?q={nome_artista}&type=artist&limit=1"
            res_search = await client.get(url_search, headers=headers)
            
            if res_search.status_code == 200:
                items = res_search.json().get("artists", {}).get("items", [])
                if not items:
                    return []
                
                artist_id = items[0]["id"]
                
                # puxa as top tracks do artista (limit=5)
                url_top_tracks = f"{self.base_url}/artists/{artist_id}/top-tracks?market=PT"
                res_tracks = await client.get(url_top_tracks, headers=headers)
                
                if res_tracks.status_code == 200:
                    tracks = res_tracks.json().get("tracks", [])
                    # captura apenas as 5 primeiras faixas (ou menos se não houver tantas)
                    for track in tracks[:5]:
                        uris_artista.append(track["uri"])
        except Exception as e:
            print(f"Erro ao processar as faixas do artista {nome_artista}: {e}")
        
        return uris_artista

    async def preencher_playlist(self, token: str, playlist_id: str, artistas_sugeridos: list) -> int:
        """Varre os 10 artistas em paralelo e injeta as 50 faixas na playlist."""
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            # usar o asyncio.gather para buscar as top tracks de todos os artistas sugeridos em paralelo
            tarefas = [
                self.buscar_top_tracks_por_artista(client, headers, artista) 
                for artista in artistas_sugeridos
            ]
            resultados = await asyncio.gather(*tarefas)
            
            # agregar todas as faixas numa lista única
            todas_as_faixas = [uri for lista in resultados for uri in lista]
            
            if todas_as_faixas:
                url_add = f"{self.base_url}/playlists/{playlist_id}/tracks"
                # adicionar as faixas à playlist (50 faixas por pedido, mas pode enviar todas de uma vez)
                res_add = await client.post(url_add, json={"uris": todas_as_faixas}, headers=headers)
                if res_add.status_code != 201:
                    print(f"Aviso ao injetar faixas na playlist: {res_add.text}")
            
            return len(todas_as_faixas)