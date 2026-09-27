import './Alerts.css';
/**
 * Alert: pieza visual reutilizable para mensajes de exito, error,
 * advertencia o información.
 *
 * Este componente NO decide cuando aparece un mensaje ni de donde
 * viene el texto (responsabilidad de cada pagina que lo use)
 * Solo diseño 
 */

// type puede ser: 'success' | 'error' | 'warning' | 'info'
function Alert({ type = 'info', message, onClose }) {
  if (!message) return null;

  return (
    <div className={`alert alert-${type}`} role="alert">
      <span>{message}</span>
      {onClose && (
        <button
          type="button"
          className="alert-close"
          onClick={onClose}
          aria-label="Cerrar mensaje"
        >
          ×
        </button>
      )}
    </div>
  );
}

export default Alert;