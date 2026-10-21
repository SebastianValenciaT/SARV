// Zonas que calcula el servidor (Reporte.zona) y el texto que se muestra.
export const ZONAS = [
  { id: 'centro', nombre: 'Centro' },
  { id: 'norte', nombre: 'Sector Norte' },
  { id: 'sur', nombre: 'Sector Sur' },
  { id: 'oriente', nombre: 'Sector Oriente' },
  { id: 'poniente', nombre: 'Sector Poniente' },
];

export function nombreZona(id) {
  return ZONAS.find((zona) => zona.id === id)?.nombre ?? '';
}
