import { useRef, useState } from 'react';
import { Marker, useMapEvents } from 'react-leaflet';
import { useGeolocation } from '../../hooks/useGeolocation';
import { buscarDireccion, direccionInversa } from '../../services/geo';
import { dentroDeJuarez, redondear6 } from '../../utils/coordenadas';
import { mensajeGeo } from '../../utils/errores';
import Icon from '../common/Icon';
import CentrarEn from '../mapa/CentrarEn';
import MapaBase from '../mapa/MapaBase';
import { crearPinIcon } from '../mapa/pinIcon';
import AvisoPrivacidadUbicacion from './AvisoPrivacidadUbicacion';
import './UbicacionPicker.css';

const PRECISION_ACEPTABLE_M = 100;
const MIN_CARACTERES_BUSQUEDA = 3;
const FUERA_DE_JUAREZ = 'Esa ubicación está fuera de Ciudad Juárez. Coloca el pin dentro de la ciudad.';

// Escucha los toques/clics en el mapa (debe ir dentro de <MapaBase>)
function ToqueEnMapa({ onToque }) {
  useMapEvents({ click: (e) => onToque(e.latlng.lat, e.latlng.lng) });
  return null;
}

/**
 * UbicacionPicker: elige la ubicación del incidente (contrato, sección 4.1).
 *
 * - value: { latitud, longitud, direccion } — latitud/longitud son null sin pin.
 * - onChange(cambios): recibe SOLO los campos que cambian; el padre los mezcla
 *   con el valor anterior (setUbicacion((prev) => ({ ...prev, ...cambios }))).
 * - error: mensaje del servidor para la ubicación (por ejemplo, fuera de Juárez).
 * - icon: ícono del pin (el del tipo de incidente elegido).
 *
 * El pin es la fuente de verdad; el texto es solo la etiqueta que verán los demás.
 */
function UbicacionPicker({ value, onChange, error, icon = 'pin' }) {
  const [cargando, setCargando] = useState(null);       // null | 'buscar' | 'inversa' | 'ubicacion'
  const [aviso, setAviso] = useState(null);             // { tipo: 'error' | 'warning', texto }
  const [candidatos, setCandidatos] = useState([]);
  const [mostrarPrivacidad, setMostrarPrivacidad] = useState(false);
  const [precisionBaja, setPrecisionBaja] = useState(null);   // metros, si el GPS fue impreciso
  const [enfoque, setEnfoque] = useState(null);         // a dónde volar el mapa (búsqueda o GPS)
  const peticionRef = useRef(null);                     // AbortController de la última consulta
  const markerRef = useRef(null);
  const geolocalizacion = useGeolocation();

  const hayPin = value.latitud != null && value.longitud != null;

  // Cancela la consulta anterior y empieza una nueva: así solo cuenta la última respuesta.
  function nuevaPeticion() {
    peticionRef.current?.abort();
    peticionRef.current = new AbortController();
    return peticionRef.current;
  }

  function cancelarPeticion() {
    peticionRef.current?.abort();
    peticionRef.current = null;
    setCargando(null);
  }

  function terminar(controller) {
    if (peticionRef.current === controller) setCargando(null);
  }

  // Coloca el pin si está dentro de Juárez. `extra` permite cambiar también la dirección.
  function colocarPin(lat, lng, extra = {}) {
    if (!dentroDeJuarez(lat, lng)) {
      setAviso({ tipo: 'error', texto: FUERA_DE_JUAREZ });
      // Si se arrastró afuera, el marcador vuelve a su lugar anterior
      if (hayPin) markerRef.current?.setLatLng([value.latitud, value.longitud]);
      return false;
    }
    setAviso(null);
    onChange({ latitud: redondear6(lat), longitud: redondear6(lng), ...extra });
    return true;
  }

  async function consultarInversa(lat, lng) {
    const controller = nuevaPeticion();
    setCargando('inversa');
    try {
      const data = await direccionInversa(redondear6(lat), redondear6(lng), { signal: controller.signal });
      onChange({ direccion: data.direccion });
    } catch (err) {
      if (controller.signal.aborted) return; // respuesta obsoleta: se ignora
      setAviso({ tipo: 'warning', texto: `${mensajeGeo(err)} Puedes escribir la dirección a mano.` });
    } finally {
      terminar(controller);
    }
  }

  // 2) Buscar la dirección escrita (solo con Enter o el botón; nunca mientras se escribe)
  async function buscar() {
    const q = (value.direccion ?? '').trim();
    if (q.length < MIN_CARACTERES_BUSQUEDA) {
      setAviso({ tipo: 'error', texto: 'Escribe al menos 3 caracteres para buscar.' });
      return;
    }
    const controller = nuevaPeticion();
    setCargando('buscar');
    setCandidatos([]);
    setPrecisionBaja(null);
    try {
      const data = await buscarDireccion(q, { signal: controller.signal });
      elegirCandidato(data.resultados[0]);
      // Calles largas tienen varios puntos: se ofrece la lista para elegir
      setCandidatos(data.resultados.length > 1 ? data.resultados : []);
    } catch (err) {
      if (controller.signal.aborted) return;
      setAviso({ tipo: 'error', texto: mensajeGeo(err) });
    } finally {
      terminar(controller);
    }
  }

  function elegirCandidato(candidato) {
    if (colocarPin(candidato.lat, candidato.lng, { direccion: candidato.direccion })) {
      setEnfoque({ latitud: candidato.lat, longitud: candidato.lng });
    }
  }

  // 3) Tocar el mapa o soltar el pin: una sola consulta inversa (no por cada pixel del arrastre)
  function moverPinA(lat, lng) {
    setPrecisionBaja(null);
    if (colocarPin(lat, lng)) consultarInversa(lat, lng);
  }

  // 1) "Usar mi ubicación actual": aviso -> permiso -> pin -> inversa
  function pedirUbicacion() {
    if (window.isSecureContext === false) {
      // Sin HTTPS el navegador no la da: se explica en vez de fallar en silencio
      geolocalizacion.solicitar().then((r) => setAviso({ tipo: 'warning', texto: r.mensaje }));
      return;
    }
    setMostrarPrivacidad(true);
  }

  async function aceptarPrivacidad() {
    setMostrarPrivacidad(false);
    cancelarPeticion();
    setCargando('ubicacion');
    const resultado = await geolocalizacion.solicitar();
    setCargando(null);
    if (!resultado.ok) {
      setAviso({ tipo: 'warning', texto: resultado.mensaje });
      return;
    }
    const { latitud, longitud, precision } = resultado;
    if (colocarPin(latitud, longitud)) {
      setEnfoque({ latitud, longitud });
      setPrecisionBaja(precision > PRECISION_ACEPTABLE_M ? Math.round(precision) : null);
      consultarInversa(latitud, longitud);
    }
  }

  // 4) Editar el texto: se respeta lo escrito. Se cancela cualquier consulta pendiente
  //    para que una respuesta tardía no sobrescriba el texto; el pin no se mueve.
  function editarTexto(e) {
    cancelarPeticion();
    onChange({ direccion: e.target.value });
  }

  function teclaEnTexto(e) {
    if (e.key === 'Enter') {
      e.preventDefault(); // dentro de un <form>, Enter enviaría el formulario
      buscar();
    }
  }

  const mensajeCarga = {
    buscar: 'Buscando la dirección…',
    inversa: 'Obteniendo la dirección del pin…',
    ubicacion: 'Obteniendo tu ubicación…',
  }[cargando];

  return (
    <div className="ubi">
      <div className="ubi-buscar">
        <label className="ubi-campo">
          <Icon name="search" />
          <input
            type="text"
            value={value.direccion}
            onChange={editarTexto}
            onKeyDown={teclaEnTexto}
            placeholder="Calle y colonia, o un lugar conocido"
            maxLength={255}
            enterKeyHint="search"
            autoComplete="off"
            aria-label="Dirección del incidente"
          />
        </label>
        <button type="button" className="btn-outline ubi-btn" onClick={buscar} disabled={cargando === 'buscar'}>
          Buscar
        </button>
      </div>

      <button type="button" className="btn-outline ubi-btn ubi-gps" onClick={pedirUbicacion} disabled={cargando === 'ubicacion'}>
        <Icon name="nav" size={15} />
        Usar mi ubicación actual
      </button>

      {mostrarPrivacidad && (
        <AvisoPrivacidadUbicacion onAceptar={aceptarPrivacidad} onCancelar={() => setMostrarPrivacidad(false)} />
      )}

      {candidatos.length > 0 && (
        <div className="ubi-candidatos">
          <div className="lbl">¿Cuál de estos lugares es?</div>
          <ul>
            {candidatos.map((c) => {
              const elegido = value.latitud === redondear6(c.lat) && value.longitud === redondear6(c.lng);
              return (
                <li key={`${c.lat},${c.lng}`}>
                  <button
                    type="button"
                    className={`ubi-candidato ${elegido ? 'on' : ''}`}
                    onClick={() => elegirCandidato(c)}
                    aria-pressed={elegido}
                  >
                    <Icon name="pin" size={15} />
                    {c.direccion}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="ubi-mapa">
        <MapaBase zoom={12}>
          <ToqueEnMapa onToque={moverPinA} />
          {hayPin && (
            <Marker
              ref={markerRef}
              position={[value.latitud, value.longitud]}
              icon={crearPinIcon(icon, true)}
              draggable
              title="Arrastra el pin para ajustar la ubicación"
              eventHandlers={{
                // Solo al SOLTAR: durante el arrastre no se consulta nada
                dragend: (e) => {
                  const { lat, lng } = e.target.getLatLng();
                  moverPinA(lat, lng);
                },
              }}
            />
          )}
          <CentrarEn latitud={enfoque?.latitud} longitud={enfoque?.longitud} zoomMinimo={16} />
        </MapaBase>
        {!hayPin && <div className="ubi-ayuda">Toca el mapa para colocar el pin</div>}
      </div>

      <div className="ubi-estado" aria-live="polite">
        {mensajeCarga && <span className="ubi-cargando">{mensajeCarga}</span>}
        {precisionBaja && (
          <span className="ubi-msg warning">
            Tu ubicación tiene una precisión de unos {precisionBaja} m. Ajusta el pin arrastrándolo al lugar exacto.
          </span>
        )}
        {aviso && <span className={`ubi-msg ${aviso.tipo}`}>{aviso.texto}</span>}
        {error && <span className="ubi-msg error">{error}</span>}
        {hayPin && (
          <span className="ubi-coords">
            Pin: {value.latitud.toFixed(6)}, {value.longitud.toFixed(6)}
          </span>
        )}
      </div>
    </div>
  );
}

export default UbicacionPicker;
