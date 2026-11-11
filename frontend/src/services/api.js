import axios from 'axios';
import { borrarSesion, guardarSesion, obtenerAccess, obtenerRefresh, tokenVigente } from './sesion';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  // Los arreglos viajan como ?tipo=1&tipo=3 (lo que espera Django),
  // no como ?tipo[]=1&tipo[]=3 (el formato por defecto de axios).
  paramsSerializer: { indexes: null },
});

/*
  Autenticación JWT. El servidor espera "Authorization: Bearer <access>".
  - Antes de cada petición se pone el access; si ya venció, primero se renueva.
  - Si aun así llega un 401, se renueva una vez y se reintenta la petición.
  - Si no se puede renovar, se borra la sesión (AuthContext se entera por
    sesion.js). La redirección a /login la decide la interfaz, nunca este archivo.
  Ojo: con un token vencido o inválido el servidor responde 401 incluso en los
  endpoints públicos; por eso no se mandan tokens vencidos y los GET se
  reintentan sin token cuando la sesión ya no sirve.
*/

// Estas rutas nunca llevan token ni se renuevan (un 401 en login = datos incorrectos)
const RUTAS_SIN_TOKEN = ['/login/', '/registro/', '/token/refresh/'];
const MARGEN_SEG = 30;   // se renueva un poco antes de que venza el access

function esRutaSinToken(url = '') {
  return RUTAS_SIN_TOKEN.some((ruta) => url.endsWith(ruta));
}

// Una sola renovación a la vez: si varias peticiones la necesitan juntas,
// todas esperan la misma promesa.
let renovando = null;

function renovar() {
  if (!renovando) {
    // axios "pelado" (no `api`): así esta petición no pasa por los interceptores
    renovando = axios
      .post(`${baseURL}/token/refresh/`, { refresh: obtenerRefresh() })
      .then(({ data }) => {
        guardarSesion(data.access, data.refresh);   // refresh solo si el servidor manda uno
        return data.access;
      })
      .catch((error) => {
        // El servidor rechazó el refresh: la sesión ya no sirve.
        // Sin respuesta (red caída) se conserva, para no cerrar sesión por estar offline.
        if (error.response) borrarSesion();
        throw error;
      })
      .finally(() => {
        renovando = null;
      });
  }
  return renovando;
}

api.interceptors.request.use(async (config) => {
  if (esRutaSinToken(config.url)) return config;

  let access = obtenerAccess();
  if (!tokenVigente(access, MARGEN_SEG)) {
    access = null;
    if (tokenVigente(obtenerRefresh())) {
      // Si falla, la petición sale sin token: lo público responde igual
      access = await renovar().catch(() => null);
    } else {
      borrarSesion();   // los dos vencieron
    }
  }

  if (access) {
    config.headers.set('Authorization', `Bearer ${access}`);
    config._conToken = true;
  } else {
    config.headers.delete('Authorization');
    config._conToken = false;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    const reintentable =
      error.response?.status === 401 &&
      config &&
      config._conToken &&          // sin token, un 401 es de un endpoint protegido
      !config._reintentado &&      // solo un reintento: nunca un bucle
      !esRutaSinToken(config.url);
    if (!reintentable) return Promise.reject(error);
    config._reintentado = true;

    if (tokenVigente(obtenerRefresh())) {
      const renovado = await renovar().then(() => true, () => false);
      // El interceptor de petición pone el access nuevo. Se reutiliza la misma
      // config: conserva el FormData y el `signal` del AbortController.
      if (renovado) return api(config);
      if (obtenerRefresh()) return Promise.reject(error);   // falló la red: se conserva la sesión
    }

    borrarSesion();
    // Sin sesión, un GET puede ser de un endpoint público: se repite sin token
    if (config.method === 'get') return api(config);
    return Promise.reject(error);
  },
);

export default api;
