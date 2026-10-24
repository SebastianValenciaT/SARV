import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/layout/Navbar'; // Importación directa del Navbar del equipo
import './Login.css';

export default function Login() {
  const location = useLocation();
  const navigate = useNavigate();
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
      const response = await fetch('http://localhost:8000/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: correo,
          password: password
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Almacenamos los tokens de sesión en el navegador
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        
        // Redirige al usuario a la página principal o ruta raíz
        navigate('/'); 
      } else {
        // Si las credenciales fallan, mostramos el error
        setError('Correo o contraseña incorrectos. Verifica tus datos.');
      }
    } catch (err) {
      console.error('Error de red:', err);
      setError('Error al conectar con el servidor. Verifica que el backend esté encendido.');
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