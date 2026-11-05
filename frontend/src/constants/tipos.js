/*
  Ícono de cada tipo de incidente, indexado por el `nombre` que devuelve
  GET /api/tipos/. Los ids siempre salen de la API, nunca se escriben aquí.
*/
export const ICONOS_TIPO = {
  Bache: 'alert',
  Choque: 'car',
  Inundación: 'drop',
  Tráfico: 'light',
  Obstrucción: 'cone',
  Otro: 'circle-alert',
};

const ICONO_POR_DEFECTO = 'circle-alert';

export function iconoTipo(nombre) {
  return ICONOS_TIPO[nombre] ?? ICONO_POR_DEFECTO;
}

// Los reportes traen solo el id del tipo; con el catálogo se obtiene su nombre.
export function iconoPorId(tipos, id) {
  const tipo = tipos?.find((t) => t.id === id);
  return iconoTipo(tipo?.nombre);
}
