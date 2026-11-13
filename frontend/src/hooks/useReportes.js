import { getReportes, getReportesMapa } from '../services/reportes';
import { useApi } from './useApi';
import { usePaginado } from './usePaginado';

// Listado paginado. filtros: { tipo: [ids], zona, fecha, estado, q }
export function useReportes(filtros) {
  return useApi(getReportes, filtros);
}

// Listado con "Cargar más": acumula páginas y se reinicia al cambiar los filtros
export function useReportesPaginados(filtros) {
  return usePaginado(getReportes, filtros);
}

// Pines del mapa (mismos filtros, solo reportes sin resolver)
export function useReportesMapa(filtros) {
  return useApi(getReportesMapa, filtros);
}
