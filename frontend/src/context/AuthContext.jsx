/*
  Estado global de la sesión del usuario.
  Guarda si hay una sesión activa, quién es el usuario (GET /api/me/) y ofrece
  las funciones login() y logout() al resto de la aplicación.
  Los tokens viven en services/sesion.js, que comparte con api.js.
*/

import { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api';
import { borrarSesion, guardarSesion, haySesion, obtenerAccess, suscribir } from '../services/sesion';

const AuthContext = createContext(null);

// Usuario aún sin confirmar con el servidor
const SIN_USUARIO = { usuario: null, listo: false };

export function AuthProvider({ children }) {
  // Al cargar la app se revisa si ya hay una sesión guardada en el navegador,
  // para que no se pierda al recargar la página. La sesión sigue mientras el
  // token de renovación (refresh) no venza, aunque el de acceso ya haya vencido:
  // api.js pide uno nuevo antes de usarlo.
  const [sesionActiva, setSesionActiva] = useState(() => {
    if (haySesion()) return true;

    // Si no hay tokens o el refresh venció, se limpian los datos y se trata como visitante
    borrarSesion();
    return false;
  });
  const [accessToken, setAccessToken] = useState(obtenerAccess);
  const [me, setMe] = useState(SIN_USUARIO);
  // Cuenta los login(): si alguien inicia sesión estando ya dentro (otra cuenta),
  // sesionActiva no cambia, pero hay que volver a pedir /me/.
  const [inicios, setInicios] = useState(0);

  // api.js renueva o borra los tokens por su cuenta (y otras pestañas también):
  // sesion.js avisa y aquí se actualiza el estado, para que el Navbar cambie al instante.
  useEffect(
    () =>
      suscribir(() => {
        const activa = haySesion();
        setSesionActiva(activa);
        setAccessToken(obtenerAccess());
        if (!activa) setMe(SIN_USUARIO);
      }),
    [],
  );

  // Con sesión, se pregunta al servidor quién es el usuario
  useEffect(() => {
    if (!sesionActiva) return;
    const controller = new AbortController();
    api
      .get('/me/', { signal: controller.signal })
      .then(({ data }) => setMe({ usuario: data, listo: true }))
      .catch(() => {
        // Un 401 ya lo resolvió api.js (borró la sesión). Si falló la red, la
        // sesión se conserva aunque no sepamos el nombre.
        if (!controller.signal.aborted) setMe({ usuario: null, listo: true });
      });
    return () => controller.abort();
  }, [sesionActiva, inicios]);

  // Inicia la sesión: guarda los tokens en el navegador y actualiza el estado.
  // Se debe usar esta función y no localStorage directo, porque es el cambio
  // de estado el que hace que el Navbar se actualice al instante.
  const login = (access, refresh) => {
    setMe(SIN_USUARIO);
    setInicios((n) => n + 1);
    guardarSesion(access, refresh);
  };

  // Cierra la sesión: elimina los tokens y limpia el estado.
  // La redirección a Inicio la hace el componente que la llama (Navbar).
  const logout = () => {
    borrarSesion();
  };

  return (
    <AuthContext.Provider
      // isAuthenticated es true mientras la sesión sea válida y false cuando no.
      // cargando es true mientras se confirma la sesión con el servidor: las
      // rutas protegidas esperan en lugar de mandar a /login antes de saber.
      value={{
        accessToken,
        isAuthenticated: sesionActiva,
        usuario: sesionActiva ? me.usuario : null,
        cargando: sesionActiva && !me.listo,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Atajo para acceder al contexto desde cualquier componente.
// (Vive junto al Provider porque Login y Navbar ya lo importan de aquí; el único
// costo es que Fast Refresh recarga la página completa al editar este archivo.)
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
