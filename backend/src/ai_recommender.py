import os
from openai import OpenAI

class AIRecommender:
    def __init__(self):
        # O cliente da OpenAI lê automaticamente a variável OPENAI_API_KEY do teu .env
        self.client = OpenAI()

    def ler_historico_local(self, caminho_arquivo="data/historico_artistas.txt"):
        """Lê o dataset local de artistas que o utilizador já conhece."""
        if not os.path.exists(caminho_arquivo):
            return set()
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            return set(linha.strip() for linha in f if linha.strip())

    def obter_recomendacoes(self):
        """Analisa o gosto musical e pede à OpenAI artistas novos e fora do radar."""
        # 1. Carrega o teu histórico completo do ficheiro gerado pelo Spotify
        artistas_conhecidos = self.ler_historico_local()
        
        if not artistas_conhecidos:
            return ["Erro: Primeiro precisas de atualizar o teu Dataset do Spotify na interface!"]

        # Pegamos numa amostra (ex: os primeiros 20 artistas) para dar contexto do teu estilo à IA
        amostra_gosto = list(artistas_conhecidos)[:20]

        # 2. Engenharia de Prompt para garantir respostas limpas que o código consiga ler
        prompt = f"""
        Atue como um recomendador de música especialista em descobrir artistas independentes, alternativos e de nicho.
        Eu já oiço e conheço muito bem estes artistas: {', '.join(amostra_gosto)}.

        Recomende uma lista de 15 artistas novos que tenham uma sonoridade parecida ou complementar a estes.
        Regra estrita: Retorne APENAS os nomes dos artistas, um por linha, sem números, sem introduções e sem explicações.
        """

        # 3. Chamada oficial à API da OpenAI (padrão de mercado para o teu currículo)
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini", # O modelo ideal: ultra rápido, inteligente e super barato
            messages=[
                {"role": "system", "content": "Você é um curador musical focado em dados brutos e limpos, que nunca adiciona texto decorativo."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        resposta_ia = completion.choices[0].message.content.strip().split('\n')

        # 4. filtrar: Excluir o que tu já conheces
        novas_descobertas = []
        for artista in resposta_ia:
            nome_limpo = artista.strip()
            # Se o artista gerado pela IA NÃO estiver no teu arquivo de texto, ele é uma descoberta real!
            if nome_limpo and nome_limpo not in artistas_conhecidos:
                novas_descobertas.append(nome_limpo)

        # Devolvemos apenas os primeiros 5 sobreviventes ao filtro para o Frontend React
        return novas_descobertas[:5]