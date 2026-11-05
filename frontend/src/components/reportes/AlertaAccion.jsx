import { Link, useLocation } from 'react-router-dom';
import Alert from '../common/Alerts';
import { esSinSesion, mensajeAccion } from '../../utils/errores';

/**
 * AvisoSesion: "Inicia sesión para continuar" con enlace a /login.
 * El enlace lleva state.from para que Login regrese a esta página.
 */
export function AvisoSesion({ onClose }) {
  const location = useLocation();
  const message = (
    <>
      Inicia sesión para continuar.{' '}
      <Link to="/login" state={{ from: location }}>
        Iniciar sesión
      </Link>
    </>
  );
  return <Alert type="warning" message={message} onClose={onClose} />;
}

/**
 * AlertaAccion: muestra el error de una acción (reaccionar, denunciar) con Alert.
 * Si falta la sesión (por ejemplo, venció y no se pudo renovar), invita a iniciarla.
 */
function AlertaAccion({ error, onClose }) {
  if (!error) return null;

  if (esSinSesion(error)) return <AvisoSesion onClose={onClose} />;

  return <Alert type="error" message={mensajeAccion(error)} onClose={onClose} />;
}

export default AlertaAccion;
