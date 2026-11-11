import { useCallback, useEffect, useState } from 'react';

/**
 * useApi: ejecuta una función de services/ y devuelve { data, loading, error, setData }.
 *
 * - `fetcher` debe ser una función de services/ (definida fuera del componente,
 *   así no cambia entre renders).
 * - `args` son sus argumentos (filtros, id...). Se convierten a texto (`key`)
 *   para que el efecto solo se repita cuando su contenido cambie de verdad.
 * - Al cambiar los argumentos o desmontar, se cancela la petición anterior
 *   (AbortController), así una respuesta vieja nunca pisa a una nueva.
 * - `setData(nuevo)` reemplaza el dato con lo que respondió el servidor después
 *   de una acción (por ejemplo, reaccionar), sin volver a "cargando". Quien no lo
 *   necesita (Lista, Mapa) simplemente no lo usa.
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

  // Cada setData "recuerda" la key del render en que se creó. Si la respuesta de
  // una acción llega tarde, cuando ya se cambió de id, la key ya no coincide y se
  // ignora (no pinta el reporte anterior). Tras desmontar, React no hace nada.
  const setData = useCallback(
    (nuevo) =>
      setResultado((anterior) =>
        anterior.key === key ? { key, data: nuevo, error: null } : anterior,
      ),
    [key],
  );

  const vigente = resultado.key === key;
  return {
    data: vigente ? resultado.data : null,
    loading: !vigente,
    error: vigente ? resultado.error : null,
    setData,
  };
}
