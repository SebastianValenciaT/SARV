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

/*
  Crea un reporte. `formData` trae los campos y las fotos (clave `imagenes`
  repetida, una por archivo). Responde con el JSON del detalle.

  ¿Por qué el header? api.js usa 'application/json' por defecto, y con ese
  header axios convertiría el FormData a JSON (los archivos se perderían).
  Al indicar multipart, axios deja el FormData intacto y el navegador escribe
  el header real con su "boundary" (el separador entre campos).
  TODO(auth): el token lo agregará el cliente de api.js cuando exista useAuth().
*/
export async function crearReporte(formData, config) {
  const { data } = await api.post('/reportes/', formData, {
    ...config,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/*
  Reacciones y denuncias. Las tres responden con el detalle actualizado
  (mismo JSON que getReporte): la página lo usa tal cual para refrescar
  conteos, mi_reaccion, ya_denuncie y estado.
  TODO(auth): requieren sesión; hasta que api.js mande el token, el servidor
  responde 403 a todos.
*/

// Crea o cambia mi reacción. tipo: 'sin_resolver' | 'resuelto'
export async function reaccionar(id, tipo, config) {
  const { data } = await api.put(`/reportes/${id}/reaccion/`, { tipo }, config);
  return data;
}

// Quita mi reacción (si no tenía, responde igual)
export async function quitarReaccion(id, config) {
  const { data } = await api.delete(`/reportes/${id}/reaccion/`, config);
  return data;
}

export async function denunciar(id, motivo, config) {
  const { data } = await api.post(`/reportes/${id}/denuncias/`, { motivo }, config);
  return data;
}
