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

/*
  ¿El error es por falta de sesión? 401, o un 403 genérico de DRF.
  Los 403 con mensaje propio del servidor traen `codigo` (por ejemplo
  'reporte_propio'): esos no son de sesión y se muestra su `detail`.
*/
export function esSinSesion(error) {
  const status = statusDe(error);
  return status === 401 || (status === 403 && !error.response.data?.codigo);
}

// Errores de reaccionar y denunciar (la falta de sesión se revisa antes con esSinSesion)
export function mensajeAccion(error) {
  const data = error?.response?.data;
  switch (statusDe(error)) {
    case 400:
      return primerMensaje(data) ?? 'Revisa los datos e intenta de nuevo.';
    case 403:
      return data?.detail ?? 'No tienes permiso para hacer esto.';
    case 404:
      return 'Este reporte ya no existe.';
    case 409:
      // reporte_resuelto o reporte_expirado: el servidor manda el mensaje de cada caso
      return data?.detail ?? 'Este reporte ya no admite cambios.';
    case 429:
      return data?.detail ?? 'Hiciste muchas acciones seguidas. Espera un momento e intenta de nuevo.';
    default:
      return 'No pudimos completar la acción. Revisa tu conexión e intenta de nuevo.';
  }
}
