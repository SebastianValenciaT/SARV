import { useEffect, useState } from 'react';
import api from './services/api';

function App() {
  const [status, setStatus] = useState('checking...');

  useEffect(() => {
    api.get('/ping/')
      .then((res) => setStatus(res.data.message))
      .catch(() => setStatus('sin conexión con el backend'));
  }, []);

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>SARV</h1>
      <p>Estado de la API: <strong>{status}</strong></p>
    </main>
  );
}

export default App;