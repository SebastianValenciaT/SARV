import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * RutaProtegida: muestra `children` solo con sesión.
 * Sin sesión manda a /login y guarda en state.from la página pedida, para que
 * Login regrese ahí al terminar. Mientras se confirma la sesión (cargando),
 * espera: así una recarga con sesión no rebota a /login.
 */
function RutaProtegida({ children }) {
  const { isAuthenticated, cargando } = useAuth();
  const location = useLocation();

  if (cargando) {
    return (
      <p role="status" style={{ padding: '24px 16px' }}>
        Comprobando tu sesión…
      </p>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

export default RutaProtegida;
