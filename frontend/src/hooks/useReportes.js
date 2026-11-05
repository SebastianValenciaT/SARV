import { getReportes, getReportesMapa } from '../services/reportes';
import { useApi } from './useApi';

// Listado paginado. filtros: { tipo: [ids], zona, fecha, estado, q }
export function useReportes(filtros) {
  return useApi(getReportes, filtros);
}

// Pines del mapa (mismos filtros, solo reportes sin resolver)
export function useReportesMapa(filtros) {
  return useApi(getReportesMapa, filtros);
}
