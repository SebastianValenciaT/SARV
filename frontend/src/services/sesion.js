/*
  sesion.js — Única fuente de verdad de los tokens JWT.

  Los guarda en localStorage (claves 'accessToken' y 'refreshToken') para que la
  sesión sobreviva a una recarga. Riesgo conocido: si la página sufriera un XSS,
  ese script podría leerlos (ver CLAUDE.md).

  api.js (fuera de React) y AuthContext leen y escriben aquí, y AuthContext se
  suscribe con suscribir() para enterarse cuando api.js renueva o cierra la sesión.
*/

const ACCESS = 'accessToken';
const REFRESH = 'refreshToken';
const listeners = new Set();

function avisar() {
  listeners.forEach((listener) => listener());
}

export function obtenerAccess() {
  return localStorage.getItem(ACCESS);
}

export function obtenerRefresh() {
  return localStorage.getItem(REFRESH);
}

// El refresh es opcional: al renovar, el servidor solo devuelve un access nuevo
export function guardarSesion(access, refresh) {
  localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
  avisar();
}

export function borrarSesion() {
  if (!obtenerAccess() && !obtenerRefresh()) return;   // ya estaba cerrada
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
  avisar();
}

// Se evalúa que el token exista y que su fecha de expiración no haya pasado
// (con `margenSeg` segundos de anticipación). Solo sirve para decidir qué hacer
// en el navegador; la validación real del token la hace el backend.
export function tokenVigente(token, margenSeg = 0) {
  // Aquí se verifica si existe un token guardado
  if (!token) return false;

  try {
    // Se toma la parte central del JWT, donde viene la fecha de expiración
    // y se convierte de base64url a base64 para poder decodificarla
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(base64));

    // Se compara la expiración (en segundos) con la hora actual (en milisegundos)
    return (payload.exp - margenSeg) * 1000 > Date.now();
  } catch {
    // Si el token está mal formado, se considera inválido
    return false;
  }
}

// Hay sesión mientras el refresh siga vigente, aunque el access ya haya vencido
// (api.js lo renueva antes de usarlo).
export function haySesion() {
  return tokenVigente(obtenerRefresh());
}

// Registra una función que se llama cada vez que la sesión cambia.
// Devuelve la función para darse de baja (útil como cleanup de un useEffect).
export function suscribir(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// Otras pestañas: el evento 'storage' llega cuando OTRA pestaña cambia
// localStorage (key null = se borró todo). Así, cerrar sesión en una cierra todas.
window.addEventListener('storage', (evento) => {
  if (evento.key === null || evento.key === ACCESS || evento.key === REFRESH) avisar();
});
