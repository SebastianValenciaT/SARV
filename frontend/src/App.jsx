import { Routes, Route } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Layout from './components/layout/Layout';
import Alert from './components/common/Alerts';
import api from './services/api';
import Inicio from './pages/Inicio'


// Funcion mientras se construyen las vistas
function Placeholder({ title }) {
  return <h2>{title} — página en construcción</h2>;
} 

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><Inicio /></Layout>} />
      <Route path="/mapa" element={<Layout><Placeholder title="Mapa" /></Layout>} />
      <Route path="/reportes" element={<Layout><Placeholder title="Reportes" /></Layout>} />
      <Route path="/login" element={<Layout><Placeholder title="Iniciar sesión" /></Layout>} />
      <Route path="/registro" element={<Layout><Placeholder title="Registrarse" /></Layout>} />
      <Route path="/mis-reportes" element={<Layout><Placeholder title="Mis reportes" /></Layout>} />
    </Routes>
  );
}

export default App;