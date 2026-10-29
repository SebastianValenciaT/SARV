import { useId, useState } from 'react';
import Alert from '../common/Alerts';
import Icon from '../common/Icon';
import AlertaAccion from './AlertaAccion';
import { denunciar } from '../../services/reportes';
import { statusDe } from '../../utils/errores';
import './DenunciaPanel.css';

// Mismos límites que el servidor (DenunciaSerializer). Se cuentan sin los
// espacios del inicio y del final, igual que en el backend.
const MIN = 10;
const MAX = 300;

function validarMotivo(texto) {
  const largo = texto.trim().length;
  if (largo === 0) return 'Escribe el motivo de la denuncia.';
  if (largo < MIN) return `El motivo debe tener al menos ${MIN} caracteres.`;
  if (largo > MAX) return `El motivo no puede pasar de ${MAX} caracteres.`;
  return null;
}

/**
 * DenunciaPanel: botón "Denunciar" del detalle que despliega el motivo
 * (sección 4.2 del documento). No se muestra al autor del reporte.
 *
 * La denuncia solo se registra; el reporte no cambia. Tras enviarla, el
 * detalle que responde el servidor trae ya_denuncie: true y el botón queda
 * como "Denuncia registrada".
 */
function DenunciaPanel({ reporte, onActualizado, onRefrescar }) {
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [intentado, setIntentado] = useState(false);   // mostrar errores solo después de enviar
  const [errorServidor, setErrorServidor] = useState(null);  // error del campo motivo (400)
  const [error, setError] = useState(null);            // cualquier otro error de axios
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState(null);
  const panelId = useId();
  const motivoId = useId();
  const ayudaId = useId();
  const errorId = useId();

  if (reporte.es_autor) return null;

  const resuelto = reporte.estado === 'resuelto';
  const largo = motivo.trim().length;
  const errorCampo = errorServidor ?? (intentado ? validarMotivo(motivo) : null);

  function cerrar() {
    setAbierto(false);
    setMotivo('');
    setIntentado(false);
    setErrorServidor(null);
  }

  async function enviar(evento) {
    evento.preventDefault();
    setIntentado(true);
    setErrorServidor(null);
    setError(null);
    if (validarMotivo(motivo)) return;

    setEnviando(true);
    try {
      const detalle = await denunciar(reporte.id, motivo.trim());
      cerrar();
      setAviso('Denuncia registrada. Gracias por avisarnos.');
      onActualizado(detalle);
    } catch (err) {
      const data = err.response?.data;
      if (statusDe(err) === 400 && data?.detail) {
        // 400 con `detail` (no con errores por campo): ya la había denunciado,
        // por ejemplo desde otra pestaña. Se trata como éxito y se vuelve a pedir
        // el detalle para que ya_denuncie venga del servidor.
        cerrar();
        setAviso('Ya habías denunciado este reporte; tu denuncia sigue registrada.');
        onRefrescar();
      } else if (statusDe(err) === 400 && data?.motivo) {
        setErrorServidor(data.motivo[0]);
      } else {
        setError(err);
        if (statusDe(err) === 409) onRefrescar();   // se resolvió mientras tanto
      }
    } finally {
      setEnviando(false);
    }
  }

  let textoBoton = 'Denunciar';
  if (reporte.ya_denuncie) textoBoton = 'Denuncia registrada';

  return (
    <div className="denuncia">
      <button
        type="button"
        className="btn-outline btn-danger detalle-denunciar"
        disabled={reporte.ya_denuncie || resuelto || abierto}
        title={resuelto && !reporte.ya_denuncie ? 'Este reporte ya está resuelto' : undefined}
        aria-expanded={reporte.ya_denuncie ? undefined : abierto}
        aria-controls={reporte.ya_denuncie ? undefined : panelId}
        onClick={() => {
          setAviso(null);
          setError(null);
          setAbierto(true);
        }}
      >
        <Icon name="alert" size={15} />
        {textoBoton}
      </button>

      {resuelto && !reporte.ya_denuncie && (
        <p className="denuncia-nota">No se puede denunciar un reporte resuelto.</p>
      )}

      <Alert type="success" message={aviso} onClose={() => setAviso(null)} />
      <AlertaAccion error={error} onClose={() => setError(null)} />

      {abierto && (
        <form id={panelId} className="card denuncia-panel" onSubmit={enviar} noValidate>
          <label htmlFor={motivoId} className="denuncia-label">
            ¿Por qué crees que este reporte es falso o dudoso?
          </label>
          <textarea
            id={motivoId}
            className="denuncia-textarea"
            rows={4}
            value={motivo}
            onChange={(e) => {
              setMotivo(e.target.value);
              setErrorServidor(null);
            }}
            aria-invalid={errorCampo ? true : undefined}
            aria-describedby={errorCampo ? `${ayudaId} ${errorId}` : ayudaId}
            disabled={enviando}
          />
          <div className="denuncia-ayuda">
            <span id={ayudaId}>Entre {MIN} y {MAX} caracteres.</span>
            <span
              className={`denuncia-contador ${largo > MAX ? 'excedido' : ''}`}
              aria-live="polite"
            >
              {largo}/{MAX}
            </span>
          </div>
          {errorCampo && (
            <p id={errorId} className="denuncia-error">
              {errorCampo}
            </p>
          )}
          <div className="denuncia-acciones">
            <button type="button" className="btn-outline" onClick={cerrar} disabled={enviando}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={enviando}>
              {enviando ? 'Enviando…' : 'Enviar denuncia'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default DenunciaPanel;
