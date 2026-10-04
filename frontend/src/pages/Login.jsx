import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Navbar from '../components/layout/Navbar'; // Importación directa del Navbar del equipo
import './Login.css';

export default function Login() {
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!correo.trim() || !password.trim()) {
      setError('Por favor, completa todos los campos.');
      return;
    }
    console.log('Intentando iniciar sesión con:', { correo, password });
  };

  return (
    <div className="login-page">
      <Navbar />

      <main className="login-content">
        <div className="login-card">
          <h1 className="login-title">Inicia Sesión en SARV</h1>

          {error && <div className="login-error-alert">{error}</div>}

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

            <div className="forgot-password-wrapper">
              <a href="#recuperar" className="forgot-password-link">
                ¿Olvidaste tu contraseña?
              </a>
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