import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/layout/Navbar'; // Importación directa del Navbar del equipo
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import './Login.css';


export default function Login() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const mensajeExito = location.state?.message || '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!correo.trim() || !password.trim()) {
      setError('Por favor, completa todos los campos.');
      return;
    }
    setError('');

    try {
      // Petición al endpoint del backend para autenticar y obtener tokens JWT
      // (api.js ya conoce la dirección del servidor)
      const { data } = await api.post('/login/', { email: correo, password });

      // Almacenamos los tokens de sesión en el navegador
      login(data.access, data.refresh);

      // Regresa a la página protegida que se pidió (RutaProtegida la guarda) o a Inicio
      navigate(location.state?.from?.pathname ?? '/', { replace: true });
    } catch (err) {
      const status = err.response?.status;
      if (status === 401) {
        // Si las credenciales fallan, mostramos el error
        setError('Correo o contraseña incorrectos. Verifica tus datos.');
      } else if (status === 429) {
        setError('Demasiados intentos de inicio de sesión. Espera un momento e intenta de nuevo.');
      } else if (!err.response) {
        setError('Error al conectar con el servidor. Verifica que el backend esté encendido.');
      } else {
        setError('No se pudo iniciar sesión. Intenta de nuevo.');
      }
    }
  };

  return (
    <div className="login-page">
      <Navbar />

      <main className="login-content">
        <div className="login-card">
          <h1 className="login-title">Inicia Sesión en SARV</h1>

          {error && <div className="login-error-alert">{error}</div>}

          {mensajeExito && (
            <div className="login-success-alert" style={{ 
              backgroundColor: '#e6f7ff', 
              color: '#0050b3', 
              padding: '10px', 
              borderRadius: '5px', 
              marginBottom: '15px',
              border: '1px solid #91d5ff'
          }}>
    {mensajeExito}
  </div>
)}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <input
                type="email"
                placeholder="Correo"
                value={correo}
                onChange={(e) => {
                  setCorreo(e.target.value);
                  if (error) setError('');
                }}
                className="login-input"
              />
            </div>

            <div className="form-group">
              <input
                type="password"
                placeholder="Contraseña"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError('');
                }}
                className="login-input"
              />
            </div>

            <button type="submit" className="btn-iniciar-sesion">
              Iniciar Sesión
            </button>
          </form>

          <div className="register-redirect">
            <span className="register-redirect-text">¿No tienes una cuenta?</span>
            <Link to="/registro" className="btn-ir-registro">
              Registrarse
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}