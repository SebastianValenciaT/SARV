import Icon from '../common/Icon';
import { iconoTipo } from '../../constants/tipos';
import './ChipsTipo.css';

/**
 * ChipsTipo: filtro de un solo tipo ("Todos" o uno del catálogo).
 * - tipos: lo que devuelve GET /api/tipos/ (se respeta su orden; los ids vienen de la API).
 * - valor: 'todos' o el id del tipo elegido. onChange recibe el nuevo valor.
 * - variante: 'envolver' (pasa a otra fila si no cabe) o 'desplazar' (una fila
 *   con scroll horizontal, para pantallas angostas y pantalla completa).
 */
function ChipsTipo({ tipos, valor, onChange, variante = 'envolver', className = '' }) {
  const opciones = [
    { valor: 'todos', nombre: 'Todos', icono: 'list' },
    ...(tipos ?? []).map((tipo) => ({ valor: tipo.id, nombre: tipo.nombre, icono: iconoTipo(tipo.nombre) })),
  ];

  return (
    <div
      className={`chips-tipo chips-tipo--${variante} ${className}`.trim()}
      role="group"
      aria-label="Filtrar por tipo de incidente"
    >
      {opciones.map((opcion) => {
        const activo = valor === opcion.valor;
        return (
          <button
            key={opcion.valor}
            type="button"
            className={`chip-tipo ${activo ? 'on' : ''}`}
            aria-pressed={activo}
            onClick={() => onChange(opcion.valor)}
          >
            <span className="chip-tipo-icon">
              <Icon name={opcion.icono} />
            </span>
            {opcion.nombre}
          </button>
        );
      })}
    </div>
  );
}

export default ChipsTipo;
