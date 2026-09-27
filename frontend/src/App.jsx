import { Routes, Route } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Layout from './components/layout/Layout';
import Alert from './components/common/Alerts';
import api from './services/api';

function Inicio() {
  const [status, setStatus] = useState('checking...');
  //comentado para prueba mensaje error alert (comentario linea 21)
  // const [showAlert, setShowAlert] = useState(true);

  useEffect(() => {
    api.get('/ping/')
      .then((res) => setStatus(res.data.message))
      .catch(() => setStatus('sin conexión con el backend'));
  }, []);

  return (
    <div>
      {/*
        DEMO temporal del componente Alert (actividad 2.4).
        mensaje de error de UC-03 (correo duplicado).
        Se deja comentado como evidencia de que el componente funciona;
        cada pagina real tendra sus propios mensajes segun su logica.
      */}
      {/* {showAlert && (
        <Alert
          type="error"
          message="El correo electrónico ya está en uso."
          onClose={() => setShowAlert(false)}
        />
      )} */}
  
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
      <Route path="/mapa" element={<Layout><Placeholder title="Mapa" /></Layout>} />
      <Route path="/reportes" element={<Layout><Placeholder title="Reportes" /></Layout>} />
      <Route path="/login" element={<Layout><Placeholder title="Iniciar sesión" /></Layout>} />
      <Route path="/registro" element={<Layout><Placeholder title="Registrarse" /></Layout>} />
      <Route path="/mis-reportes" element={<Layout><Placeholder title="Mis reportes" /></Layout>} />
    </Routes>
  );
}

export default App;