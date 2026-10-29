import { ESTADOS } from '../../constants/estados';
import './EstadoBadge.css';

/**
 * EstadoBadge: etiqueta de color con el estado del reporte
 * (Sin resolver, Resuelto o Expirado), tal como lo manda la API.
 */
function EstadoBadge({ estado, className = '' }) {
  const info = ESTADOS[estado];
  if (!info) return null;
  return <span className={`estado-badge ${info.clase} ${className}`.trim()}>{info.texto}</span>;
}

export default EstadoBadge;
