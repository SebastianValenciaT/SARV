import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  // simulado por el momento (cambiar useState a true para ver navbar usuario autenticado)
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          SARV
        </Link>

        <div className="navbar-right">
          <ul className="navbar-links">
            <li>
              <NavLink to="/" end className="navbar-link">
                Inicio
              </NavLink>
            </li>
            <li>
              <NavLink to="/mapa" className="navbar-link">
                Mapa
              </NavLink>
            </li>
            <li>
              <NavLink to="/reportes" className="navbar-link">
                Reportes
              </NavLink>
            </li>

            {isAuthenticated && (
              <li>
                <NavLink to="/mis-reportes" className="navbar-link">
                  Mis reportes
                </NavLink>
              </li>
            )}

            <li>
              {isAuthenticated ? (
                <button
                  type="button"
                  className="navbar-link navbar-link-button"
                  onClick={() => setIsAuthenticated(false)}
                >
                  Cerrar sesión
                </button>
              ) : (
                <NavLink to="/login" className="navbar-link">
                  Iniciar sesión
                </NavLink>
              )}
            </li>
          </ul>

          {isAuthenticated ? (
            <NavLink to="/crear-reporte" className="navbar-cta">
              Reportar
            </NavLink>
          ) : (
            <NavLink to="/registro" className="navbar-cta">
              Registrarse
            </NavLink>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;