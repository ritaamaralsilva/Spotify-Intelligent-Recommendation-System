import React, { useState } from 'react';

interface ApiResponse {
  status: string;
  total_artistas?: number;
  recommendations?: string[];
  message?: string;
}

function App() {
  const [loadingScan, setLoadingScan] = useState<boolean>(false);
  const [loadingRecommend, setLoadingRecommend] = useState<boolean>(false);
  const [totalArtistas, setTotalArtistas] = useState<number | null>(null);
  const [descobertas, setDescobertas] = useState<string[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  // 1. Chamar a rota de Scan do Spotify
  const handleScan = async () => {
    setLoadingScan(true);
    setErro(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/scan');
      const data: ApiResponse = await res.json();
      
      if (data.status === 'success') {
        setTotalArtistas(data.total_artistas ?? 0);
      } else {
        setErro(data.message || 'Erro ao sincronizar com o Spotify.');
      }
    } catch (err) {
      setErro('Não foi possível conectar ao servidor Backend.');
    } finally {
      setLoadingScan(false);
    }
  };

  // 2. Chamar a rota da OpenAI para obter recomendações
  const handleRecommend = async () => {
    setLoadingRecommend(true);
    setErro(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/recommend');
      const data: ApiResponse = await res.json();
      
      if (data.status === 'success') {
        setDescobertas(data.recommendations || []);
      } else {
        setErro(data.message || 'Erro ao obter recomendações da IA.');
      }
    } catch (err) {
      setErro('Não foi possível conectar ao servidor Backend.');
    } finally {
      setLoadingRecommend(false);
    }
  };

  return (
    <div style={{
      backgroundColor: '#121212',
      color: '#FFFFFF',
      minHeight: '100vh',
      fontFamily: 'Arial, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '40px 20px'
    }}>
      <header style={{ marginBottom: '40px', textAlign: 'center' }}>
        <h1 style={{ color: '#1DB954', fontSize: '2.5rem', marginBottom: '10px' }}>Spotify Recommendation System </h1>
        <p style={{ color: '#B3B3B3' }}>Descobre novos artistas fora do teu radar usando Inteligência Artificial</p>
      </header>

      <main style={{ maxWidth: '600px', width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {erro && (
          <div style={{ backgroundColor: '#E91429', padding: '12px', borderRadius: '4px', textAlign: 'center' }}>
            {erro}
          </div>
        )}

        {/* Secção de Sincronização */}
        <div style={{ backgroundColor: '#181818', padding: '24px', borderRadius: '8px', border: '1px solid #282828' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '12px' }}>1. Sincronizar Biblioteca</h2>
          <p style={{ color: '#B3B3B3', fontSize: '0.9rem', marginBottom: '16px' }}>
            Mapeia as tuas playlists e músicas que gostaste para criares o teu histórico musical.
          </p>
          <button 
            onClick={handleScan}
            disabled={loadingScan}
            style={{
              backgroundColor: '#1DB954',
              color: '#FFFFFF',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '50px',
              fontWeight: 'bold',
              cursor: loadingScan ? 'not-allowed' : 'pointer',
              opacity: loadingScan ? 0.7 : 1,
              width: '100%'
            }}
          >
            {loadingScan ? 'A ler Spotify (isto pode demorar)...' : 'Sincronizar com Spotify'}
          </button>
          
          {totalArtistas !== null && (
            <p style={{ color: '#1DB954', marginTop: '12px', textAlign: 'center', fontWeight: 'bold' }}>
              ✓ Mapeados {totalArtistas} artistas com sucesso!
            </p>
          )}
        </div>

        {/* Secção de Recomendações */}
        <div style={{ backgroundColor: '#181818', padding: '24px', borderRadius: '8px', border: '1px solid #282828' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '12px' }}>2. Gerar Descobertas com IA</h2>
          <p style={{ color: '#B3B3B3', fontSize: '0.9rem', marginBottom: '16px' }}>
            O GPT-4o mini vai analisar o teu gosto e sugerir 5 artistas novos que nunca ouviste.
          </p>
          <button 
            onClick={handleRecommend}
            disabled={loadingRecommend}
            style={{
              backgroundColor: '#FFFFFF',
              color: '#000000',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '50px',
              fontWeight: 'bold',
              cursor: loadingRecommend ? 'not-allowed' : 'pointer',
              opacity: loadingRecommend ? 0.7 : 1,
              width: '100%'
            }}
          >
            {loadingRecommend ? 'A IA está a pensar...' : 'Gerar Recomendações Inéditas'}
          </button>

          {descobertas.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <h3 style={{ fontSize: '1rem', color: '#B3B3B3', marginBottom: '10px' }}>Artistas Recomendados:</h3>
              <ul style={{ listStyleType: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {descobertas.map((artista, index) => (
                  <li 
                    key={index} 
                    style={{ 
                      backgroundColor: '#282828', 
                      padding: '12px 16px', 
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      fontWeight: 'bold'
                    }}
                  >
                    <span style={{ color: '#1DB954', marginRight: '12px' }}>#{index + 1}</span>
                    {artista}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
