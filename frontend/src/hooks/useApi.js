import { useEffect, useState } from 'react';

/**
 * useApi: ejecuta una función de services/ y devuelve { data, loading, error }.
 *
 * - `fetcher` debe ser una función de services/ (definida fuera del componente,
 *   así no cambia entre renders).
 * - `args` son sus argumentos (filtros, id...). Se convierten a texto (`key`)
 *   para que el efecto solo se repita cuando su contenido cambie de verdad.
 * - Al cambiar los argumentos o desmontar, se cancela la petición anterior
 *   (AbortController), así una respuesta vieja nunca pisa a una nueva.
 */
export function useApi(fetcher, ...args) {
  const key = JSON.stringify(args);
  // Guardamos a qué `key` pertenece el resultado: si no coincide, aún está cargando.
  const [resultado, setResultado] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    fetcher(...JSON.parse(key), { signal: controller.signal })
      .then((data) => setResultado({ key, data, error: null }))
      .catch((error) => {
        if (!controller.signal.aborted) setResultado({ key, data: null, error });
      });
    return () => controller.abort();
  }, [fetcher, key]);

  const vigente = resultado.key === key;
  return {
    data: vigente ? resultado.data : null,
    loading: !vigente,
    error: vigente ? resultado.error : null,
  };
}
