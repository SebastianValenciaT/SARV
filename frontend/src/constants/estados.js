// Estados que devuelve la API (`estado` efectivo de lista y detalle) y cómo se muestran.
// `expirado` lo calcula el servidor según la duración del tipo (no se guarda).
// La clase da el color en components/common/EstadoBadge.css.
export const ESTADOS = {
  sin_resolver: { texto: 'Sin resolver', clase: 'estado-sin-resolver' },
  resuelto: { texto: 'Resuelto', clase: 'estado-resuelto' },
  expirado: { texto: 'Expirado', clase: 'estado-expirado' },
};

// Reacciones y denuncias solo se permiten en reportes sin resolver y vigentes (RN-14).
export function esSoloLectura(estado) {
  return estado === 'resuelto' || estado === 'expirado';
}
