import { NavLink } from 'react-router-dom';
import Icon from '../common/Icon';
import './ReportesHeader.css';

/**
 * ReportesHeader: titulo, conteo de reportes y herramientas (filtros,
 * cambio Mapa/Lista y busqueda). Compartido por las vistas /mapa y /reportes.
 * La busqueda se envia al presionar Enter: onBuscar recibe el texto.
 */
function ReportesHeader({ total, etiqueta = 'reportes', filtrosActivos = 0, onToggleFiltros, onBuscar }) {
  const buscar = (event) => {
    event.preventDefault(); // evita que el formulario recargue la pagina
    const texto = new FormData(event.currentTarget).get('q');
    onBuscar?.(texto.trim());
  };

  return (
    <header className="reportes-head">
      <div>
        <h1>Mapa y reportes</h1>
        <div className="reportes-head-sub">
          <span className="reportes-head-dot" />
          <b>{total ?? '…'}</b> {etiqueta} &nbsp;Ciudad Juárez
        </div>
      </div>

      <div className="reportes-head-tools">
        <button type="button" className="reportes-tool-btn" onClick={onToggleFiltros}>
          <Icon name="sliders" />
          Filtros
          {filtrosActivos > 0 && <span className="reportes-badge">{filtrosActivos}</span>}
        </button>

        <div className="reportes-toggle">
          <NavLink to="/mapa" className="reportes-toggle-item">
            <Icon name="map" />
            Mapa
          </NavLink>
          <NavLink to="/reportes" end className="reportes-toggle-item">
            <Icon name="list" />
            Lista
          </NavLink>
        </div>

        <form className="reportes-search" role="search" onSubmit={buscar}>
          <Icon name="search" />
          <input type="search" name="q" placeholder="Buscar por calle o título" maxLength={100} />
        </form>
      </div>
    </header>
  );
}

export default ReportesHeader;
