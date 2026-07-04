# Spotify Recommendation System

Uma aplicação full-stack desenvolvida para resolver um problema comum de transição entre plataformas de streaming: o "cold start" do algoritmo.
Após importar um histórico massivo da Apple Music para uma conta recente do Spotify, este sistema analisou a biblioteca importada para gerar recomendações musicais através de Modelos de Linguagem (LLMs), garantindo que nenhuma sugestão duplica artistas que o utilizador já conhece.
Foi um projeto pessoal que senti necessidade de criar visto que esta conta do Spotify ainda não estava mapeada de acordo com os meus gostos para me poder recomendar artistas novos, mas que também me parece bastante útil para quem queira descobrir artistas novos que possa gostar.

## Arquitetura do Sistema

O projeto adota uma arquitetura desacoplada (*decoupled*) dividida em dois serviços principais:

1. **Backend (FastAPI + Python):** 
   - Autenticação e consumo da API do Spotify via fluxos OAuth2.
   - Algoritmo de paginação para extração em massa (mapeamento de +1500 artistas únicos a partir de uma biblioteca de ~10k faixas).
   - Pipeline de processamento de dados que injeta o histórico limpo no prompt da OpenAI (`gpt-4o-mini`).
   - Filtro pós-geração para garantir a exclusão estrita de duplicados.

2. **Frontend (React + TypeScript):**
   - Interface SPA com design *dark mode* otimizado.
   - Gestão de estados assíncronos para lidar com o tempo de processamento das APIs externas.

---

## Tecnologias Utilizadas

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI, Uvicorn
- **APIs Externas:** Spotify Web API (`spotipy`), OpenAI API

---

## Desafios Técnicos Resolvidos

- **Paginação e Resiliência (Spotify API):** A extração inicial de grandes volumes de faixas disparava facilmente limites da API. Foi implementada uma lógica de paginação de 50 em 50 faixas com controlo de estado local para garantir que a leitura de grandes bibliotecas terminava sem corromper o histórico.
- **Tratamento de Rate Limiting:** Configuração e gestão do ciclo de vida dos tokens OAuth2 através de cache local (`.cache`) para mitigar pedidos repetidos de autenticação e evitar bloqueios temporários por parte do Spotify.
- **Determinismo no Output da IA:** Engenharia de prompts estruturada com foco em dados brutos para forçar a API da OpenAI a devolver estritamente uma lista limpa de strings, eliminando textos decorativos ou preâmbulos conversacionais que quebrariam o parsing no frontend.

---

## Como Executar o Projeto

### Pré-requisitos
- Python 3.10+
- Node.js & npm
- Contas de Developer no Spotify e na OpenAI

### 1. Configuração do Backend

1. Navega até à pasta do backend:
   ```bash
   cd backend
   ```
2. Cria e ativa o teu ambiente virtual:
   ```bash
   python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
3. Instala as dependências:
```bash
pip install -r requirements.txt
```
4. Cria um ficheiro .env com as tuas credenciais:
```bash
SPOTIPY_CLIENT_ID="teu_client_id"
SPOTIPY_CLIENT_SECRET="teu_client_secret"
SPOTIPY_REDIRECT_URI="[http://127.0.0.1:8000/callback](http://127.0.0.1:8000/callback)"
OPENAI_API_KEY="tua_chave_openai"
```
5. Inicia o servidor:
```bash
python main.py
```
### 1. Configuração do Frontend

1. Numa nova aba do terminal, navega até à pasta do frontend:
```bash
cd frontend
```
2. Instala as dependências:
```bash
npm install
```
3. Inicia o servidor de desenvolvimento:
```bash
npm run dev
```
Acede ao endereço indicado pelo Vite no terminal (ex: http://localhost:5173) para testar a aplicação.

---

## 📄 Licença

Este projeto está sob a licença MIT - consulta o ficheiro [LICENSE](LICENSE) para mais detalhes.

---

### Desenvolvido por Rita Silva com 🤍






  
