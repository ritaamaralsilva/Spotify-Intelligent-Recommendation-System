import React, { useState, useEffect } from 'react';

interface GenreStat {
  genre: string;
  count: number;
  percentage: number;
}

interface ApiResponse {
  status: string;
  total_artistas?: number;
  message?: string;
  playlist_url?: string;
  tracks_count?: number;
  artists_discovered?: string[];
  top_genres?: GenreStat[];
}

// Definir a URL base da API do backend (apenas hardcoded em fase de dev e testes)
const API_BASE_URL = 'http://127.0.0.1:8000';

function App() {
  // null = ainda não sabemos, false = não autenticado, true = autenticado
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  const [loadingScan, setLoadingScan] = useState<boolean>(false);
  const [loadingRecommend, setLoadingRecommend] = useState<boolean>(false);
  const [totalArtistas, setTotalArtistas] = useState<number | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [playlistName, setPlaylistName] = useState<string>('My AI Discovery Mix');
  const [playlistUrl, setPlaylistUrl] = useState<string | null>(null);
  const [artistasDescobertos, setArtistasDescobertos] = useState<string[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // estado para armazenar as estatísticas de géneros do utilizador e estudo de mercado
  const [statsGeneros, setStatsGeneros] = useState<GenreStat[]>([]);

  // Ao montar o componente, verifica se já existe uma sessão válida
  useEffect(() => {
    checkSession();
  }, []);

  // Login tem de ser feito com navegação real do browser, NUNCA com fetch,
  // porque o fluxo OAuth do Spotify envolve redirects para um domínio externo
  // que não devolve headers CORS para o nosso frontend.
  const handleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/login`;
  };

  // Verifica se a sessão está ativa tentando carregar as estatísticas.
  // Se der 401, mostramos o ecrã de login; se der sucesso, mostramos a app.
  const checkSession = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stats/genres`, { credentials: 'include' });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      const data: ApiResponse = await res.json();
      setIsAuthenticated(true);
      if (data.status === 'success' && data.top_genres) {
        setStatsGeneros(data.top_genres);
      }
    } catch (err) {
      // erro de rede/CORS distingue-se de um 401: aqui assumimos que o
      // backend pode estar em baixo, mas mantemos o utilizador no ecrã de login
      setIsAuthenticated(false);
      setErro('Não foi possível conectar ao servidor Backend.');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stats/genres`, { credentials: 'include' });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      const data: ApiResponse = await res.json();
      if (data.status === 'success' && data.top_genres) {
        setStatsGeneros(data.top_genres);
      }
    } catch (err) {
      console.error('Erro ao carregar estatísticas:', err);
    }
  };

  const handleScan = async () => {
    setLoadingScan(true);
    setErro(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/scan`, { credentials: 'include' });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      const data: ApiResponse = await res.json();

      if (data.status === 'success') {
        setTotalArtistas(data.total_artistas ?? 0);
        fetchStats(); // atualiza as estatísticas de géneros após a sincronização
      } else {
        setErro(data.message || 'Erro ao sincronizar com o Spotify.');
      }
    } catch (err) {
      setErro('Não foi possível conectar ao servidor Backend.');
    } finally {
      setLoadingScan(false);
    }
  };

  const handleGeneratePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (playlistName.trim() === '') {
      setErro('Por favor, dá um nome à tua playlist.');
      return;
    }

    setLoadingRecommend(true);
    setErro(null);
    setPlaylistUrl(null);
    setSuccessMessage(null);
    setArtistasDescobertos([]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/recommend/generate-playlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // garante que o cookie de sessão é enviado
        body: JSON.stringify({ playlist_name: playlistName }),
      });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      const data: ApiResponse = await res.json();

      if (data.status === 'success') {
        setPlaylistUrl(data.playlist_url || null);
        setArtistasDescobertos(data.artists_discovered || []);
        setSuccessMessage(`Sucesso! Criámos a tua playlist com ${data.tracks_count} músicas baseadas em 10 artistas emergentes.`);
      } else {
        setErro(data.message || 'Erro ao obter recomendações da IA.');
      }
    } catch (err) {
      setErro('Não foi possível conectar ao servidor Backend.');
    } finally {
      setLoadingRecommend(false);
    }
  };

  const pageStyle: React.CSSProperties = {
    backgroundColor: '#121212',
    color: '#FFFFFF',
    width: '100%',
    minHeight: '100dvh',
    fontFamily: 'Arial, sans-serif',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 20px',
    boxSizing: 'border-box',
  };

  // Ecrã de arranque: ainda não sabemos se há sessão válida
  if (isAuthenticated === null) {
    return (
      <div style={pageStyle}>
        <p style={{ color: '#B3B3B3' }}>A verificar sessão...</p>
      </div>
    );
  }

  // Ecrã de login: sem sessão válida, mostra apenas o botão de entrar com Spotify
  if (isAuthenticated === false) {
    return (
      <div style={{ ...pageStyle, justifyContent: 'center', minHeight: '100dvh' }}>
        <header style={{ marginBottom: '40px', textAlign: 'center' }}>
          <h1 style={{ color: '#1DB954', fontSize: '2.5rem', marginBottom: '10px' }}>Spotify Recommendation System</h1>
          <p style={{ color: '#B3B3B3' }}>Análise de Tendências e Descoberta de Artistas Emergentes com IA</p>
        </header>

        {erro && (
          <div style={{ backgroundColor: '#E91429', padding: '12px', borderRadius: '4px', textAlign: 'center', fontWeight: 'bold', marginBottom: '20px', maxWidth: '400px' }}>
            {erro}
          </div>
        )}

        <button
          onClick={handleLogin}
          style={{
            backgroundColor: '#1DB954',
            color: '#FFFFFF',
            border: 'none',
            padding: '14px 32px',
            borderRadius: '50px',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          Entrar com Spotify
        </button>
      </div>
    );
  }

  // Ecrã principal: sessão autenticada
  return (
    <div style={pageStyle}>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <header style={{ marginBottom: '40px', textAlign: 'center' }}>
        <h1 style={{ color: '#1DB954', fontSize: '2.5rem', marginBottom: '10px' }}>Spotify Recommendation System </h1>
        <p style={{ color: '#B3B3B3' }}>Análise de Tendências e Descoberta de Artistas Emergentes com IA</p>
      </header>

      <main style={{ maxWidth: '800px', width: '100%', display: 'grid', gridTemplateColumns: statsGeneros.length > 0 ? '1fr 320px' : '1fr', gap: '20px', alignItems: 'start' }}>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {erro && (
            <div style={{ backgroundColor: '#E91429', padding: '12px', borderRadius: '4px', textAlign: 'center', fontWeight: 'bold' }}>
              {erro}
            </div>
          )}

          {/* Sincronização */}
          <div style={{ backgroundColor: '#181818', padding: '24px', borderRadius: '8px', border: '1px solid #282828' }}>
            <h2 style={{ color: '#B3B3B3', fontSize: '1.2rem', marginBottom: '12px' }}>1. Sincronizar Biblioteca</h2>
            <button
              onClick={handleScan}
              disabled={loadingScan}
              style={{
                backgroundColor: '#1DB954', color: '#FFFFFF', border: 'none', padding: '12px 24px', borderRadius: '50px', fontWeight: 'bold', cursor: loadingScan ? 'not-allowed' : 'pointer', opacity: loadingScan ? 0.7 : 1, width: '100%'
              }}
            >
              {loadingScan ? 'A processar dados no MySQL...' : 'Sincronizar com Spotify'}
            </button>
            {totalArtistas !== null && (
              <p style={{ color: '#1DB954', marginTop: '12px', textAlign: 'center', fontWeight: 'bold' }}>
                ✓ {totalArtistas} artistas catalogados na Azure!
              </p>
            )}
          </div>

          {/* Geração de Playlist */}
          <div style={{ backgroundColor: '#181818', padding: '24px', borderRadius: '8px', border: '1px solid #282828', position: 'relative' }}>
            <h2 style={{ color: '#B3B3B3', fontSize: '1.2rem', marginBottom: '12px' }}>2. Criar Playlist de Descobertas</h2>

            {loadingRecommend && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '30px 0' }}>
                <div style={{
                  border: '4px solid rgba(255, 255, 255, 0.1)',
                  borderTop: '4px solid #1DB954',
                  borderRadius: '50%',
                  width: '40px',
                  height: '40px',
                  animation: 'spin 1s linear infinite',
                  marginBottom: '16px'
                }} />
                <p style={{ color: '#B3B3B3', fontSize: '0.9rem', textAlign: 'center' }}>
                  A consultar artistas emergentes e a estruturar uma playlist de descoberta...
                </p>
              </div>
            )}

            {!loadingRecommend && (
              <form onSubmit={handleGeneratePlaylist} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <input
                  type="text"
                  value={playlistName}
                  onChange={(e) => setPlaylistName(e.target.value)}
                  placeholder="Nome da Playlist"
                  style={{ backgroundColor: '#282828', color: '#FFFFFF', border: '1px solid #404040', padding: '12px 16px', borderRadius: '4px', fontSize: '1rem', outline: 'none' }}
                />
                <button type="submit" style={{ backgroundColor: '#FFFFFF', color: '#000000', border: 'none', padding: '12px 24px', borderRadius: '50px', fontWeight: 'bold', cursor: 'pointer', width: '100%' }}>
                  Gerar Playlist de Descobertas no Spotify
                </button>
              </form>
            )}

            {successMessage && (
              <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#282828', borderRadius: '6px', borderLeft: '4px solid #1DB954' }}>
                <p style={{ color: '#1DB954', fontWeight: 'bold', marginBottom: '12px' }}>{successMessage}</p>
                {playlistUrl && (
                  <a href={playlistUrl} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block', backgroundColor: '#1DB954', color: '#FFFFFF', textDecoration: 'none', padding: '10px 20px', borderRadius: '50px', fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '16px' }}>
                    Abrir Playlist no Spotify
                  </a>
                )}
                {artistasDescobertos.length > 0 && (
                  <ul style={{ listStyleType: 'none', padding: 0, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {artistasDescobertos.map((art, idx) => (
                      <li key={idx} style={{ backgroundColor: '#121212', padding: '8px 12px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold' }}>
                        <span style={{ color: '#1DB954', marginRight: '6px' }}>#{idx + 1}</span>{art}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Coluna da Direita: Dashboard de Estudo de Mercado */}
        {statsGeneros.length > 0 && (
          <div style={{ backgroundColor: '#181818', padding: '24px', borderRadius: '8px', border: '1px solid #282828' }}>
            <h2 style={{ color: '#1DB954', fontSize: '1.2rem', marginBottom: '4px' }}>Analytics</h2>
            <p style={{ color: '#B3B3B3', fontSize: '0.8rem', marginBottom: '20px' }}>Mapa dos Gostos Musicais & Tendência Pessoal</p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {statsGeneros.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', fontWeight: 'bold' }}>
                    <span style={{ textTransform: 'capitalize' }}>{item.genre}</span>
                    <span style={{ color: '#B3B3B3' }}>{item.percentage}%</span>
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: '#282828', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${item.percentage}%`, height: '100%', backgroundColor: '#1DB954', borderRadius: '3px', transition: 'width 1s ease-in-out' }} />
                  </div>
                </div>
              ))}
            </div>
            <p style={{ color: '#6A6A6A', fontSize: '0.75rem', marginTop: '20px', textAlign: 'center', lineHeight: '1.4' }}>
              Estes são os teus géneros favoritos. A IA usa esta lista como bússola para te garantir descobertas 100% personalizadas e fora do circuito comercial (mainstream). 🎧
            </p>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;