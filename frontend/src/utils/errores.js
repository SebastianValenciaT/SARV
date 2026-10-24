/*
  errores.js — Convierte errores de axios en textos para mostrar.
  error.response.status es el código HTTP; error.response.data, el JSON de DRF.
*/

export function statusDe(error) {
  return error?.response?.status;
}

// Primer mensaje de un error 400 de DRF: { campo: ['mensaje'] } o { detail: 'mensaje' }
export function primerMensaje(data) {
  if (!data || typeof data !== 'object') return null;
  if (typeof data.detail === 'string') return data.detail;
  const primero = Object.values(data)[0];
  return Array.isArray(primero) ? primero[0] : null;
}

// Errores de geo/buscar y geo/inversa
export function mensajeGeo(error) {
  switch (statusDe(error)) {
    case 400:
      return primerMensaje(error.response.data) ?? 'Revisa lo que escribiste.';
    case 404:
      return error.response.data?.detail ?? 'No encontramos esa dirección en Ciudad Juárez.';
    case 429:
      return 'Hiciste muchas búsquedas seguidas. Espera un minuto e intenta de nuevo.';
    case 503:
      return 'El servicio de direcciones no está disponible ahora. Coloca el pin a mano y escribe la dirección.';
    default:
      return 'No pudimos consultar la dirección. Revisa tu conexión o coloca el pin a mano.';
  }
}
