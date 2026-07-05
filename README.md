# Spotify Recommendation System

Uma aplicação full-stack desenvolvida para resolver um problema comum de transição entre plataformas de streaming: o "cold start" do algoritmo.
Após importar um histórico massivo da Apple Music para uma conta recente do Spotify, este sistema analisou a biblioteca importada para gerar recomendações musicais através de Modelos de Linguagem (LLMs), garantindo que nenhuma sugestão duplica artistas que o utilizador já conhece.
Foi um projeto pessoal que senti necessidade de criar visto que esta conta do Spotify ainda não estava mapeada de acordo com os meus gostos para me poder recomendar artistas novos, mas que também me parece bastante útil para quem queira descobrir artistas novos que possa gostar de forma personalizada.

## Arquitetura do Sistema

O projeto adota uma arquitetura desacoplada (*decoupled*) dividida em três camadas principais:

1. **Backend (FastAPI + Python):** 
   - Autenticação e consumo da API do Spotify via fluxos OAuth2.
   - Algoritmo de paginação para extração em massa (mapeamento de +1500 artistas únicos a partir de uma biblioteca de ~10k faixas).
   - Pipeline de processamento de dados que injeta o histórico limpo e mapeamento no prompt da OpenAI (`gpt-4o-mini`).
   - Filtro pós-geração para garantir a exclusão estrita de duplicados.
   - Integração com ORM (SQLAlchemy) para persistência de dados.

2. **Frontend (React + TypeScript):**
   - Interface SPA com design *dark mode* otimizado.
   - Gestão de estados assíncronos para lidar com o tempo de processamento das APIs externas.

3. **Base de Dados (MySQL na Azure):**
   - Base de dados relacional alojada em cloud (Microsoft Azure) com integridade referencial estrita e eliminações em cascata (`ondelete="CASCADE"`).
   - Armazenamento centralizado do histórico de scans, mapeamento global de artistas com os seus respetivos géneros e registo de playlists geradas pela IA.

---

## Tecnologias Utilizadas

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, PyMySQL
- **Base de Dados:** MySQL (Hosted on Microsoft Azure)
- **APIs Externas:** Spotify Web API (`httpx`), OpenAI API

---

## Estrutura da Base de Dados (Modelos)

O sistema utiliza quatro entidades principais mapeadas relacionalmente para garantir eficiência e controlo:

*   **`users`:** Regista o utilizador do Spotify e controla as janelas temporais de segurança para novos scans.
*   **`artists`:** Biblioteca global que armazena os nomes dos artistas e os seus géneros musicais específicos, servindo de filtro estético para a IA.
*   **`user_artists`:** Tabela de associação (Muitos-para-Muitos) que conecta cada utilizador aos artistas que ele realmente escuta.
*   **`generated_playlists`:** Histórico persistente das playlists criadas pela Inteligência Artificial, guardando os IDs e URLs diretos do Spotify.

---

## Desafios Técnicos & Funcionalidades Resolvidas

- **Paginação e Resiliência (Spotify API):** A extração inicial de grandes volumes de faixas disparava facilmente limites da API. Foi implementada uma lógica de paginação de 50 em 50 faixas com controlo de estado local para garantir que a leitura de grandes bibliotecas terminava sem corromper o histórico.
- **Filtro de Afinidade e Bloqueio de Outliers (Anti-Géneros musicais que o user à partida não gosta):** Para evitar que a IA recomendasse artistas desalinhados com o gosto do utilizador baseando-se apenas em popularidade geográfica regional, o sistema extrai e mapeia os **géneros musicais** de cada artista. O prompt da OpenAI foi estruturado como um contrato estrito que utiliza estes géneros para barrar ruídos estéticos.
- **Geração Automatizada de Playlists:** O sistema não se limita a sugerir nomes em texto. A API consome as sugestões da OpenAI, pesquisa as *Top Tracks* desses artistas no Spotify e cria automaticamente uma Playlist real na conta do utilizador (com título customizável pelo frontend), recorrendo a permissões de escrita OAuth2 (`playlist-modify`).
- **Persistência na Cloud e Controlo de Abuso:** Migração dos ficheiros locais para um servidor MySQL na Azure. Implementação do campo `next_scan_allowed_at` na BD para impedir que pedidos repetidos ao backend atinjam as quotas das APIs externas (OpenAI e Spotify) (rate limiters).

---

## Como Executar o Projeto

### Pré-requisitos
- Python 3.10+
- Node.js & npm
- Instância MySQL ativa (Local ou Cloud)
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
4. Cria um ficheiro .env com as tuas credenciais e seguintes variáveis:
```bash
FRONTEND_URL="http://localhost:5173"
BACKEND_URL="[http://127.0.0.1:8000](http://127.0.0.1:8000)"

SPOTIFY_CLIENT_ID="o_teu_client_id"
SPOTIFY_CLIENT_SECRET="0_teu_cliente_secreto"
SPOTIFY_REDIRECT_URI="[http://127.0.0.1:8000/api/callback](http://127.0.0.1:8000/api/callback)"

OPENAI_API_KEY="a_tua_chave_do_openai"

# Conexão MySQL (Exemplo Azure/Local)
DATABASE_URL="mysql+pymysql://utilizador:password@servidor-azure:3306/nome_da_bd?ssl_ca=path/to/cacert.pem"
```
5. Inicia o servidor (a base de dados será criada automaticamente no arranque via SQLAlchemy):
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
