import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from './useApi';

const SIN_EXTRAS = { base: null, paginas: [], cargando: false, error: null };

/**
 * usePaginado: lista paginada de DRF ({count, next, previous, results}) con "Cargar más".
 *
 * - `fetcher(params, config)` es una función de services/ (por ejemplo getReportes).
 * - La página 1 la pide useApi tal cual: mismos estados de carga y error, y se
 *   vuelve a pedir sola cuando cambian los `params` (filtros).
 * - Las páginas siguientes se piden con `cargarMas()`, como `?page=N` a través del
 *   mismo fetcher (pasa por la instancia `api`: token, baseURL, interceptores).
 *   No seguimos la URL `next` completa; solo la usamos para saber si hay más.
 *
 * ¿Cómo se reinicia al cambiar un filtro? Las páginas extra se guardan junto con la
 * respuesta de la página 1 a la que pertenecen (`base`). Con filtros nuevos useApi
 * trae otra respuesta (otro objeto), así que las extras viejas ya no coinciden y se
 * ignoran. Una respuesta de "cargar más" que llegue tarde tampoco coincide: se descarta.
 *
 * Devuelve { items, count, hayMas, loading, error, cargandoMas, errorMas, cargarMas }.
 * `loading` y `error` son solo de la página 1; `errorMas` es el de "cargar más".
 */
export function usePaginado(fetcher, params) {
  const { data: primera, loading, error } = useApi(fetcher, params);
  const [extras, setExtras] = useState(SIN_EXTRAS);

  // Candado: guarda la `base` que está cargando más. Un useRef cambia al instante
  // (sin esperar a que React vuelva a renderizar), así el doble clic no pide dos veces.
  const candado = useRef(null);
  const controllerRef = useRef(null);

  // Al cambiar los filtros (nueva página 1) o desmontar: cancela el "cargar más" en curso.
  useEffect(() => {
    const ref = controllerRef;
    return () => ref.current?.abort();
  }, [primera]);

  // Solo valen las extras que pertenecen a la página 1 que se muestra ahora.
  const vigentes = primera && extras.base === primera ? extras : SIN_EXTRAS;
  const ultima = vigentes.paginas.at(-1) ?? primera;

  const cargarMas = useCallback(() => {
    if (!primera || !ultima?.next || candado.current === primera) return;
    const base = primera;
    const pagina = vigentes.paginas.length + 2; // la 1 ya está; cada extra suma una
    const controller = new AbortController();
    candado.current = base;
    controllerRef.current = controller;
    setExtras({ base, paginas: vigentes.paginas, cargando: true, error: null });

    // Solo actualiza si las extras siguen siendo de esta misma página 1.
    const siSigueVigente = (cambio) =>
      setExtras((prev) => (prev.base === base ? { ...prev, ...cambio(prev) } : prev));

    fetcher({ ...params, page: pagina }, { signal: controller.signal })
      .then((data) => siSigueVigente((prev) => ({ paginas: [...prev.paginas, data], cargando: false })))
      .catch((err) => {
        // Si se canceló (cambió el filtro), no es un error que mostrar.
        if (!controller.signal.aborted) siSigueVigente(() => ({ cargando: false, error: err }));
      })
      .finally(() => {
        if (candado.current === base) candado.current = null;
      });
  }, [fetcher, params, primera, ultima, vigentes.paginas]);

  // Une todas las páginas y quita repetidos por id: si alguien crea un reporte
  // entre una página y otra, todo se recorre un lugar y uno saldría dos veces.
  const items = useMemo(() => {
    if (!primera) return [];
    const vistos = new Set();
    return [primera, ...vigentes.paginas]
      .flatMap((pagina) => pagina.results)
      .filter((item) => (vistos.has(item.id) ? false : vistos.add(item.id)));
  }, [primera, vigentes.paginas]);

  return {
    items,
    count: ultima?.count ?? null, // la respuesta más reciente trae el total más actual
    hayMas: Boolean(ultima?.next),
    loading,
    error,
    cargandoMas: vigentes.cargando,
    errorMas: vigentes.error,
    cargarMas,
  };
}
