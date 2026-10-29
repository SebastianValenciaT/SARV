import { Link } from 'react-router-dom';
import Alert from '../common/Alerts';
import { esSinSesion, mensajeAccion } from '../../utils/errores';

/**
 * AlertaAccion: muestra el error de una acción (reaccionar, denunciar) con Alert.
 * Si falta la sesión, invita a iniciarla con un enlace a /login.
 *
 * TODO(auth): mientras api.js no mande el token, el servidor responde 403 a todos,
 * así que también quien ya inició sesión verá "Inicia sesión para continuar".
 */
function AlertaAccion({ error, onClose }) {
  if (!error) return null;

  if (esSinSesion(error)) {
    const message = (
      <>
        Inicia sesión para continuar. <Link to="/login">Iniciar sesión</Link>
      </>
    );
    return <Alert type="warning" message={message} onClose={onClose} />;
  }

  return <Alert type="error" message={mensajeAccion(error)} onClose={onClose} />;
}

export default AlertaAccion;
