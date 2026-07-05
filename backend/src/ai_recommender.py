import os
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Artist, UserArtist, GeneratedPlaylist

class AIRecommender:
    def __init__(self):
        self.client = OpenAI()

    def obter_recomendacoes(self, db: Session, spotify_id: str):
        """Analisa o gosto de forma ultra-otimizada em tokens e pede recomendações à OpenAI."""
        
        # filtro de artistas que o user já conhece para evitar recomendações redundantes
        artistas_db = (
            db.query(Artist.name)
            .join(UserArtist, Artist.id == UserArtist.artist_id)
            .filter(UserArtist.spotify_id == spotify_id)
            .all()
        )
        artistas_conhecidos = {row.name for row in artistas_db}
        
        if not artistas_conhecidos:
            return []

        # query para obter os géneros musicais dos artistas mais ouvidos do user
        # a query é feita de forma a minimizar o número de tokens enviados para a OpenAI, evitando enviar listas longas de artistas ou géneros repetidos.
        generos_db = (
            db.query(Artist.genres)
            .join(UserArtist, Artist.id == UserArtist.artist_id)
            .filter(UserArtist.spotify_id == spotify_id)
            .all()
        )
        
        # contabiliza a frequência de cada género
        contagem_generos = {}
        for row in generos_db:
            if row.genres:
                # se os géneros estiverem separados por vírgula, divide e contabiliza cada um
                for g in [gen.strip() for gen in row.genres.split(",")]:
                    contagem_generos[g] = contagem_generos.get(g, 0) + 1
        
        # amostra de 15 géneros mais ouvidos para o prompt
        generos_top = sorted(contagem_generos, key=contagem_generos.get, reverse=True)[:15]
        
        # amostra de artistas conhecidos para o prompt (até 30)
        amostra_artistas = list(artistas_conhecidos)[:30]

        # prompt para a OpenAI (leve para minimizar tokens gastos e maximizar a relevância e eficiência)
        prompt = f"""
        Atuas como um curador de música underground. Sugere 10 artistas EMERGENTES (popularidade < 40/100 no Spotify).
        
        Perfil do Utilizador (Bússola Estética):
        - Géneros Dominantes: {', '.join(generos_top)}
        - Alguns Artistas de Referência: {', '.join(amostra_artistas)}

        REGRAS:
        1. Baseia-te estritamente nos Géneros Dominantes para evitar ruído local/pimba ou pop comercial.
        2. Devolve APENAS um array JSON de strings com os nomes dos artistas, sem markdown, sem explicações.

        Formato: ["Nome 1", "Nome 2"]
        """

        # chamada à API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "És um curador focado em micro-nichos e artistas independentes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            conteudo_resposta = response.choices[0].message.content.strip()
            artistas_sugeridos = json.loads(conteudo_resposta)
            
            # o filtro de exclusão local: remove artistas que o user já conhece
            novas_descobertas = []
            for artista in artistas_sugeridos:
                nome_limpo = artista.strip()
                if nome_limpo and nome_limpo not in artistas_conhecidos:
                    novas_descobertas.append(nome_limpo)
            
            return novas_descobertas[:10]
            
        except Exception as e:
            print(f"Erro: {e}")
            return []