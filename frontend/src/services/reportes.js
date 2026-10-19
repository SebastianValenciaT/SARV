/*
  reportes.js — Llamadas a la API de reportes. Los componentes no usan axios
  directamente: piden los datos a través de los hooks de src/hooks/.
  Cada función acepta un `config` opcional de axios (por ejemplo { signal }
  para cancelar la petición) y devuelve solo `response.data`.
*/
import api from './api';

// Quita los filtros vacíos para no mandar cosas como ?zona=&q=
function limpiarParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, valor]) =>
      Array.isArray(valor) ? valor.length > 0 : valor !== '' && valor != null,
    ),
  );
}

export async function getTipos(config) {
  const { data } = await api.get('/tipos/', config);
  return data;
}

// Respuesta paginada: { count, next, previous, results }
export async function getReportes(params, config) {
  const { data } = await api.get('/reportes/', { ...config, params: limpiarParams(params) });
  return data;
}

export async function getReporte(id, config) {
  const { data } = await api.get(`/reportes/${id}/`, config);
  return data;
}

// Sin paginar: arreglo de pines (solo reportes sin resolver)
export async function getReportesMapa(params, config) {
  const { data } = await api.get('/mapa/reportes/', { ...config, params: limpiarParams(params) });
  return data;
}
