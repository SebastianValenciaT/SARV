import { useEffect } from 'react';

/**
 * usePantallaCompleta: lo que necesita un elemento que ocupa toda la pantalla con CSS.
 *
 * Mientras `activo` es true:
 * - Bloquea el scroll de la página (overflow: hidden en <html> y <body>).
 * - Marca como `inert` todo lo que queda detrás: desde el elemento de `ref` sube
 *   hasta <body> y en cada nivel marca a sus hermanos (Navbar, Footer, encabezado,
 *   lista...). Lo inerte no recibe foco con Tab ni clics.
 * - Escape llama a `onSalir` (debe ser estable: useCallback).
 *
 * Todo se deshace en el cleanup del efecto: al salir, al desmontar (navegar a otra
 * ruta) y en el doble montaje de React StrictMode. Los valores previos se guardan
 * dentro de cada ejecución del efecto, así nunca se mezclan y la página no queda bloqueada.
 */
export function usePantallaCompleta(activo, ref, onSalir) {
  useEffect(() => {
    if (!activo || !ref.current) return undefined;

    const html = document.documentElement;
    const body = document.body;
    const previo = {
      overflowHtml: html.style.overflow,
      overflowBody: body.style.overflow,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
    };
    html.style.overflow = 'hidden';
    body.style.overflow = 'hidden';

    // Solo se quitan al salir los `inert` que pusimos aquí (si alguno ya lo era, se respeta).
    const marcados = [];
    for (let nodo = ref.current; nodo.parentElement && nodo !== body; nodo = nodo.parentElement) {
      for (const hermano of nodo.parentElement.children) {
        if (hermano !== nodo && !hermano.hasAttribute('inert')) {
          hermano.setAttribute('inert', '');
          marcados.push(hermano);
        }
      }
    }

    const alPulsarTecla = (evento) => {
      if (evento.key === 'Escape') onSalir();
    };
    document.addEventListener('keydown', alPulsarTecla);

    return () => {
      document.removeEventListener('keydown', alPulsarTecla);
      marcados.forEach((elemento) => elemento.removeAttribute('inert'));
      html.style.overflow = previo.overflowHtml;
      body.style.overflow = previo.overflowBody;
      window.scrollTo(previo.scrollX, previo.scrollY);
    };
  }, [activo, ref, onSalir]);
}
