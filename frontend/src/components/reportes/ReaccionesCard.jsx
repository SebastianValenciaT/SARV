import { useId, useState } from 'react';
import Icon from '../common/Icon';
import AlertaAccion from './AlertaAccion';
import { esSoloLectura } from '../../constants/estados';
import { quitarReaccion, reaccionar } from '../../services/reportes';
import { statusDe } from '../../utils/errores';

const TILES = [
  { tipo: 'sin_resolver', etiqueta: 'Sin resolver', icono: 'flag', clase: '' },
  { tipo: 'resuelto', etiqueta: 'Resuelto', icono: 'shield', clase: 'ok' },
];

// Texto del title de cada tile según quién lo ve y el estado del reporte
function tituloTile(tile, reporte) {
  if (reporte.estado === 'resuelto') return 'Este reporte ya está resuelto';
  if (reporte.estado === 'expirado') return 'Este reporte expiró';
  if (reporte.es_autor) {
    return tile.tipo === 'resuelto'
      ? 'Marcar mi reporte como resuelto'
      : 'Como autor no reaccionas a tu reporte: usa «Resuelto» cuando se solucione';
  }
  return reporte.mi_reaccion === tile.tipo ? 'Quitar mi reacción' : `Reaccionar: ${tile.etiqueta}`;
}

/**
 * ReaccionesCard: tarjeta "Reaccionar a este reporte" del detalle.
 *
 * - Usuario ajeno: pulsar el tile activo quita la reacción (DELETE) y pulsar
 *   el otro la cambia (PUT).
 * - Autor: "Resuelto" pide confirmación y marca el reporte como resuelto;
 *   "Sin resolver" queda deshabilitado.
 * - Sin actualizaciones optimistas: lo que se ve es siempre la respuesta del
 *   servidor, que llega a la página con `onActualizado(detalle)`.
 *
 * La página la monta con key={reporte.id}: al cambiar de reporte, el estado
 * local (petición en curso, confirmación, error) empieza de cero.
 */
function ReaccionesCard({ reporte, onActualizado, onRefrescar }) {
  const [enviando, setEnviando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [error, setError] = useState(null);
  const notaId = useId();

  const soloLectura = esSoloLectura(reporte.estado);   // resuelto o expirado (RN-14)
  const esAutor = reporte.es_autor;

  async function enviar(accion) {
    setEnviando(true);
    setError(null);
    try {
      onActualizado(await accion());
    } catch (err) {
      setError(err);
      // 409: se resolvió o expiró mientras tanto; se pide el detalle para mostrarlo.
      if (statusDe(err) === 409) onRefrescar();
    } finally {
      setEnviando(false);
    }
  }

  function pulsar(tipo) {
    if (esAutor) {
      if (tipo === 'resuelto') setConfirmando(true);
      return;
    }
    if (reporte.mi_reaccion === tipo) {
      enviar(() => quitarReaccion(reporte.id));
    } else {
      enviar(() => reaccionar(reporte.id, tipo));
    }
  }

  function confirmarResuelto() {
    setConfirmando(false);
    enviar(() => reaccionar(reporte.id, 'resuelto'));
  }

  let nota = null;
  if (reporte.estado === 'resuelto') {
    nota = 'Este reporte ya está resuelto; ya no admite reacciones ni denuncias.';
  } else if (reporte.estado === 'expirado') {
    nota = 'Este reporte expiró; ya no admite reacciones ni denuncias.';
  } else if (esAutor) nota = 'Eres el autor: pulsa «Resuelto» cuando el problema ya esté solucionado.';

  return (
    <div className="card detalle-react">
      <div className="lbl">Reaccionar a este reporte</div>
      <div className="detalle-react-tiles">
        {TILES.map((tile) => {
          const activo = reporte.mi_reaccion === tile.tipo;
          const deshabilitado =
            soloLectura || enviando || confirmando || (esAutor && tile.tipo === 'sin_resolver');
          const total = reporte.reacciones[tile.tipo];
          return (
            <button
              key={tile.tipo}
              type="button"
              className={`detalle-rt ${tile.clase} ${activo ? 'on' : ''}`}
              disabled={deshabilitado}
              title={tituloTile(tile, reporte)}
              aria-label={`${tile.etiqueta}: ${total} ${total === 1 ? 'reacción' : 'reacciones'}`}
              // Para el autor no es un interruptor sino una acción: sin aria-pressed.
              aria-pressed={esAutor ? undefined : activo}
              aria-describedby={nota ? notaId : undefined}
              onClick={() => pulsar(tile.tipo)}
            >
              <span className="detalle-rt-num">{total}</span>
              <Icon name={tile.icono} />
              <span className="detalle-rt-label">{tile.etiqueta}</span>
            </button>
          );
        })}
      </div>

      {nota && (
        <p id={notaId} className="detalle-react-nota">
          {nota}
        </p>
      )}

      {confirmando && (
        <div className="detalle-react-confirm" role="group" aria-label="Confirmar reporte resuelto">
          <p aria-live="polite">¿Marcar como resuelto? No se puede deshacer.</p>
          <div className="row detalle-react-confirm-actions">
            <button type="button" className="btn-primary" onClick={confirmarResuelto}>
              Confirmar
            </button>
            <button type="button" className="btn-outline" onClick={() => setConfirmando(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {enviando && <p className="detalle-react-nota" aria-live="polite">Guardando…</p>}

      <div className="detalle-react-alert">
        <AlertaAccion error={error} onClose={() => setError(null)} />
      </div>
    </div>
  );
}

export default ReaccionesCard;
