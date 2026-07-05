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
        """Cria uma playlist vazia e privada na conta do utilizador atual.

        NOTA: desde a migração da API do Spotify de Março de 2026, o endpoint
        POST /users/{user_id}/playlists foi removido para apps em Development Mode.
        A substituição é POST /me/playlists, que cria sempre a playlist para o
        utilizador autenticado (o spotify_user_id já não vai no URL, mas mantém-se
        o parâmetro para não quebrar quem chama esta função)."""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "name": nome_playlist,
            "description": "Gerada por Spotify Intelligent Recommendation System - Descobertas emergentes fora do radar.",
            "public": False
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/me/playlists",
                json=payload,
                headers=headers
            )
            if res.status_code != 201:
                raise Exception(f"Erro ao criar playlist: {res.text}")
            dados = res.json()
            return dados["id"], dados["external_urls"]["spotify"]

    async def buscar_top_tracks_por_artista(self, client: httpx.AsyncClient, headers: dict, nome_artista: str) -> list:
        """Procura até 5 faixas de um artista pelo nome.

        NOTA: o endpoint GET /artists/{id}/top-tracks foi removido pela Spotify
        (migração de Março de 2026) sem qualquer substituto oficial. Em alternativa,
        pesquisamos diretamente faixas do artista via /search (que continua
        disponível) e usamos os resultados mais relevantes como aproximação às
        'melhores faixas'. Não é garantido que sejam as mais populares, mas é a
        única opção viável para apps em Development Mode."""
        uris_artista = []
        try:
            # pesquisa direta por faixas do artista (limite máximo atual da API é 10)
            url_search = f"{self.base_url}/search?q=artist:\"{nome_artista}\"&type=track&limit=10"
            res_search = await client.get(url_search, headers=headers)

            if res_search.status_code == 200:
                tracks = res_search.json().get("tracks", {}).get("items", [])
                # captura apenas as 5 primeiras faixas devolvidas pela pesquisa
                for track in tracks[:5]:
                    if track and track.get("uri"):
                        uris_artista.append(track["uri"])
            else:
                print(f"Aviso na pesquisa de faixas de {nome_artista}: {res_search.status_code} - {res_search.text}")
        except Exception as e:
            print(f"Erro ao processar as faixas do artista {nome_artista}: {e}")

        return uris_artista

    async def preencher_playlist(self, token: str, playlist_id: str, artistas_sugeridos: list) -> int:
        """Varre os 10 artistas em paralelo e injeta as faixas encontradas na playlist."""
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            # usar o asyncio.gather para buscar as faixas de todos os artistas sugeridos em paralelo
            tarefas = [
                self.buscar_top_tracks_por_artista(client, headers, artista)
                for artista in artistas_sugeridos
            ]
            resultados = await asyncio.gather(*tarefas)

            # agregar todas as faixas numa lista única
            todas_as_faixas = [uri for lista in resultados for uri in lista]

            if todas_as_faixas:
                # NOTA: endpoint renomeado de /playlists/{id}/tracks para /playlists/{id}/items
                # na migração da API do Spotify de Março de 2026.
                url_add = f"{self.base_url}/playlists/{playlist_id}/items"
                res_add = await client.post(url_add, json={"uris": todas_as_faixas}, headers=headers)
                if res_add.status_code != 201:
                    print(f"Aviso ao injetar faixas na playlist: {res_add.text}")

            return len(todas_as_faixas)