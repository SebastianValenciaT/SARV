import { getTipos } from '../services/reportes';
import { useApi } from './useApi';

// Catálogo de tipos de incidente: [{ id, nombre }]
export function useTipos() {
  return useApi(getTipos);
}
