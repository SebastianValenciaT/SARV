/*
  Estado global de la sesión del usuario.
  Guarda si hay una sesión activa (según el token de acceso) y ofrece
  las funciones login() y logout() al resto de la aplicación.
 
*/

import { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

// Se evalúa que el token exista y que su fecha de expiración no haya pasado.
// Solo sirve para decidir qué mostrar en la interfaz; la validación real
// del token la hace el backend en cada petición protegida.
function tokenValido(token) {
  // Aquí se verifica si existe un token guardado
  if (!token) return false;

  try {
    // Se toma la parte central del JWT, donde viene la fecha de expiración
    // y se convierte de base64url a base64 para poder decodificarla
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(base64));

    // Se compara la expiración (en segundos) con la hora actual (en milisegundos)
    return payload.exp * 1000 > Date.now();
  } catch {
    // Si el token está mal formado, se considera inválido
    return false;
  }
}

export function AuthProvider({ children }) {
  // Al cargar la app se revisa si ya hay una sesión guardada en el navegador,
  // para que no se pierda al recargar la página
  const [accessToken, setAccessToken] = useState(() => {
    const token = localStorage.getItem('accessToken');

    // Si el token sigue vigente, se conserva la sesión
    if (tokenValido(token)) return token;

    // Si venció o no es válido, se limpian los datos y se trata como visitante
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    return null;
  });

  // Inicia la sesión: guarda los tokens en el navegador y actualiza el estado.
  // Se debe usar esta función y no localStorage directo, porque es el cambio
  // de estado el que hace que el Navbar se actualice al instante.
  const login = (access, refresh) => {
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
    setAccessToken(access);
  };

  // Cierra la sesión: elimina los tokens y limpia el estado.
  // La redirección a Inicio la hace el componente que la llama (Navbar).
  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setAccessToken(null);
  };

  return (
    <AuthContext.Provider
      // isAuthenticated es true cuando existe un token y false cuando no
      value={{ accessToken, isAuthenticated: !!accessToken, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Atajo para acceder al contexto desde cualquier componente
export const useAuth = () => useContext(AuthContext);