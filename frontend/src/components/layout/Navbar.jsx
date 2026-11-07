import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import Icon from '../common/Icon';
import './Navbar.css';

function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  // Menú de celular: se guarda la ruta en la que se abrió. Al navegar a otra ruta
  // deja de coincidir y el menú queda cerrado solo (sin useEffect).
  const [abiertoEn, setAbiertoEn] = useState(null);
  const menuAbierto = abiertoEn === pathname;
  const cerrarMenu = () => setAbiertoEn(null);
  const alternarMenu = () => setAbiertoEn(menuAbierto ? null : pathname);

  const handleLogout = () => {
    cerrarMenu();
    logout();
    navigate('/');
  };

  return (
    <nav
      className="navbar"
      onKeyDown={(e) => {
        if (e.key === 'Escape') cerrarMenu();
      }}
    >
      {/* Fondo invisible detrás del menú abierto: tocar fuera lo cierra */}
      {menuAbierto && <div className="navbar-backdrop" onClick={cerrarMenu} aria-hidden="true" />}

      <div className="navbar-container">
        <Link to="/" className="navbar-brand" onClick={cerrarMenu}>
          SARV
        </Link>

        <div className="navbar-right">
          <ul id="navbar-menu" className={`navbar-links ${menuAbierto ? 'navbar-links--abierto' : ''}`.trim()}>
            <li>
              <NavLink to="/" end className="navbar-link" onClick={cerrarMenu}>
                Inicio
              </NavLink>
            </li>
            <li>
              <NavLink to="/mapa" className="navbar-link" onClick={cerrarMenu}>
                Mapa
              </NavLink>
            </li>
            {isAuthenticated && (
              <li>
                <NavLink to="/mis-reportes" className="navbar-link" onClick={cerrarMenu}>
                  Mis reportes
                </NavLink>
              </li>
            )}

            <li>
              {isAuthenticated ? (
                <button
                  type="button"
                  className="navbar-link navbar-link-button"
                  onClick={handleLogout}
                >
                  Cerrar sesión
                </button>
              ) : (
                <NavLink to="/login" className="navbar-link" onClick={cerrarMenu}>
                  Iniciar sesión
                </NavLink>
              )}
            </li>
          </ul>

          {isAuthenticated ? (
            <NavLink to="/crear-reporte" className="navbar-cta" onClick={cerrarMenu}>
              Reportar
            </NavLink>
          ) : (
            <NavLink to="/registro" className="navbar-cta" onClick={cerrarMenu}>
              Registrarse
            </NavLink>
          )}

          {/* Solo se ve en celular (Navbar.css) */}
          <button
            type="button"
            className="navbar-toggle"
            aria-expanded={menuAbierto}
            aria-controls="navbar-menu"
            aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
            onClick={alternarMenu}
          >
            <Icon name={menuAbierto ? 'close' : 'menu'} />
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
