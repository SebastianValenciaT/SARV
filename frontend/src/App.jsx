import { Routes, Route } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Layout from './components/layout/Layout';
import MapaReportes from './pages/MapaReportes';
import ListaReportes from './pages/ListaReportes';
import DetalleReporte from './pages/DetalleReporte';
import CrearReporte from './pages/CrearReporte';
import api from './services/api';
import Login from './pages/Login';
import Registro from './pages/Registro';

function Inicio() {
  const [status, setStatus] = useState('checking...');

  useEffect(() => {
    api.get('/ping/')
      .then((res) => setStatus(res.data.message))
      .catch(() => setStatus('sin conexión con el backend'));
  }, []);

  return (
    <div>
      <h1>SARV</h1>
      <p>Estado de la API: {status} </p>
    </div>
  );
}

// Funcion mientras se construyen las vistas
function Placeholder({ title }) {
  return <h2>{title} — página en construcción</h2>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><Inicio /></Layout>} />
<<<<<<< HEAD
      <Route path="/mapa" element={<Layout><MapaReportes /></Layout>} />
      <Route path="/reportes" element={<Layout><ListaReportes /></Layout>} />
      <Route path="/reportes/:id" element={<Layout><DetalleReporte /></Layout>} />
      <Route path="/crear-reporte" element={<Layout><CrearReporte /></Layout>} />
      <Route path="/login" element={<Layout><Placeholder title="Iniciar sesión" /></Layout>} />
      <Route path="/registro" element={<Layout><Placeholder title="Registrarse" /></Layout>} />
=======
      <Route path="/mapa" element={<Layout><Placeholder title="Mapa" /></Layout>} />
      <Route path="/reportes" element={<Layout><Placeholder title="Reportes" /></Layout>} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
>>>>>>> origin/Inicio_de_sesion
      <Route path="/mis-reportes" element={<Layout><Placeholder title="Mis reportes" /></Layout>} />
    </Routes>
  );
}

export default App;