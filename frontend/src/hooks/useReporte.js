import { getReporte } from '../services/reportes';
import { useApi } from './useApi';

// Detalle de un reporte. Si no existe, error.response.status === 404.
// setData(detalle) reemplaza el reporte con la respuesta de una acción (reaccionar, denunciar).
export function useReporte(id) {
  return useApi(getReporte, id);
}
