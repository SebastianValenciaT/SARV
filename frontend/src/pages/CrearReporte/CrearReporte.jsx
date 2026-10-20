import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import 'leaflet/dist/leaflet.css';
import Alert from '../../components/common/Alerts';
import './CrearReporte.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [31.4899, -106.4146];
const DEFAULT_ZOOM = 15;

const TIPOS_INCIDENTE = [
  { value: 'bache', label: 'Bache' },
  { value: 'inundacion', label: 'Inundación' },
  { value: 'semaforo', label: 'Semáforo dañado' },
  { value: 'alumbrado', label: 'Alumbrado público' },
  { value: 'obstruccion', label: 'Obstrucción vial' },
  { value: 'accidente', label: 'Accidente' },
  { value: 'otro', label: 'Otro' },
];

const NIVELES_GRAVEDAD = [
  { value: 'leve', label: 'Leve' },
  { value: 'moderado', label: 'Moderado' },
  { value: 'grave', label: 'Grave' },
];

const MAX_IMAGE_MB = 5;

const REQUIRED_FIELDS = [
  { field: 'titulo', label: 'título' },
  { field: 'tipo', label: 'tipo de incidente' },
  { field: 'gravedad', label: 'nivel de gravedad' },
  { field: 'fecha', label: 'fecha' },
  { field: 'hora', label: 'hora' },
  { field: 'descripcion', label: 'descripción' },
  { field: 'ubicacion', label: 'ubicación' },
];

const initialForm = {
  titulo: '',
  tipo: '',
  gravedad: 'moderado',
  fecha: '',
  hora: '',
  descripcion: '',
  ubicacion: '',
  lat: null,
  lng: null,
};

function UploadIcon(props) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 16V4" />
      <path d="m7 9 5-5 5 5" />
      <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function ArrowLeftIcon(props) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </svg>
  );
}

function ArrowRightIcon(props) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18&addressdetails=0`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.display_name || null;
  } catch {
    return null;
  }
}

function CrearReporte() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);

  const [form, setForm] = useState(initialForm);
  const [useMyLocation, setUseMyLocation] = useState(false);
  const [pinPlaced, setPinPlaced] = useState(false);
  const [locatingAddress, setLocatingAddress] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [alert, setAlert] = useState(null);

  const updateField = (field) => (e) => { setForm((prev) => ({ ...prev, [field]: e.target.value })); };

  const handleSeveritySelect = (value) => { setForm((prev) => ({ ...prev, gravedad: value })); };

  const setLocation = async (lat, lng) => {
    setPinPlaced(true);
    setForm((prev) => ({ ...prev, lat, lng, ubicacion: `${lat.toFixed(5)}, ${lng.toFixed(5)}` }));

    setLocatingAddress(true);
    const address = await reverseGeocode(lat, lng);
    setLocatingAddress(false);

    if (address) { setForm((prev) => ({ ...prev, ubicacion: address })); }
  };

  const placeMarker = (lat, lng) => {
    const map = mapRef.current;
    if (!map) return;

    if (!markerRef.current) {
      markerRef.current = L.marker([lat, lng], { draggable: true }).addTo(map);
      markerRef.current.on('dragend', () => {
        const pos = markerRef.current.getLatLng();
        setUseMyLocation(false);
        setLocation(pos.lat, pos.lng);
      });
    } else {
      markerRef.current.setLatLng([lat, lng]);
    }

    setLocation(lat, lng);
  };

  useEffect(() => {
    if (mapRef.current || !mapContainerRef.current) return;

    const map = L.map(mapContainerRef.current).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    map.on('click', (e) => {
      setUseMyLocation(false);
      placeMarker(e.latlng.lat, e.latlng.lng);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (alert) window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [alert]);

  const handleToggleMyLocation = (e) => {
    const checked = e.target.checked;
    setUseMyLocation(checked);

    if (!checked) return;

    if (!navigator.geolocation) {
      setAlert({ type: 'error', message: 'Tu navegador no permite obtener tu ubicación actual.' });
      setUseMyLocation(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        mapRef.current?.flyTo([latitude, longitude], 17);
        placeMarker(latitude, longitude);
      },
      () => {
        setAlert({ type: 'error', message: 'No se pudo obtener tu ubicación actual.' });
        setUseMyLocation(false);
      }
    );
  };

  const handleFile = (file) => {
    if (!file) return;

    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setAlert({ type: 'error', message: 'La imagen debe ser formato JPG o PNG.' });
      return;
    }

    if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
      setAlert({ type: 'error', message: `La imagen no debe superar ${MAX_IMAGE_MB} MB.` });
      return;
    }

    setImagePreview({ name: file.name, url: URL.createObjectURL(file) });
  };

  const handleFileInputChange = (e) => {
    handleFile(e.target.files?.[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const handleRemoveImage = (e) => {
    e.stopPropagation();
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDiscard = () => {
    setForm(initialForm);
    setUseMyLocation(false);
    setPinPlaced(false);
    setImagePreview(null);
    navigate('/mapa');
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const faltantes = REQUIRED_FIELDS
      .filter(({ field }) => !String(form[field] ?? '').trim())
      .map(({ label }) => label);

    if (faltantes.length) {
      setAlert({ type: 'error', message: `Completa los campos obligatorios: ${faltantes.join(', ')}.` });
      return;
    }

    setAlert({ type: 'success', message: 'Reporte enviado correctamente.' });
  };

  return (
    <div className="crear-reporte-page">
      <Link to="/mapa" className="crear-reporte-back">
        <ArrowLeftIcon />
        Volver a Mapa y reportes
      </Link>

      <h1 className="crear-reporte-title">Crear nuevo reporte</h1>

      {alert && (
        <Alert type={alert.type} message={alert.message} onClose={() => setAlert(null)} />
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="crear-reporte-grid">
          <div className="crear-reporte-col">
            <div className="card">
              <div className="form-field">
                <label htmlFor="titulo">
                  Título del reporte <span className="required">*</span>
                </label>
                <input
                  id="titulo"
                  type="text"
                  placeholder="Ej. Bache profundo obstaculizando carril rápido"
                  value={form.titulo}
                  onChange={updateField('titulo')}
                  required
                />
                <p className="field-hint">Describe de manera breve y clara el incidente principal.</p>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label htmlFor="tipo">
                    Tipo de incidente <span className="required">*</span>
                  </label>
                  <select id="tipo" value={form.tipo} onChange={updateField('tipo')} required>
                    <option value="" disabled>Seleccionar tipo</option>
                    {TIPOS_INCIDENTE.map((tipo) => (
                      <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
                    ))}
                  </select>
                </div>

                <div className="form-field">
                  <label>
                    Nivel de gravedad <span className="required">*</span>
                  </label>
                  <div className="severity-group" role="radiogroup" aria-label="Nivel de gravedad">
                    {NIVELES_GRAVEDAD.map((nivel) => (
                      <button
                        key={nivel.value}
                        type="button"
                        role="radio"
                        aria-checked={form.gravedad === nivel.value}
                        className={`severity-option${form.gravedad === nivel.value ? ' active' : ''}`}
                        onClick={() => handleSeveritySelect(nivel.value)}
                      >
                        {nivel.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label htmlFor="fecha">
                    Fecha del incidente <span className="required">*</span>
                  </label>
                  <input
                    id="fecha"
                    type="date"
                    value={form.fecha}
                    onChange={updateField('fecha')}
                    required
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="hora">
                    Hora aproximada <span className="required">*</span>
                  </label>
                  <input
                    id="hora"
                    type="time"
                    value={form.hora}
                    onChange={updateField('hora')}
                    required
                  />
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="descripcion">
                  Descripción detallada <span className="required">*</span>
                </label>
                <textarea
                  id="descripcion"
                  rows={5}
                  placeholder="Ingresa detalles específicos que puedan ayudar a las autoridades o vecinos a comprender el riesgo..."
                  value={form.descripcion}
                  onChange={updateField('descripcion')}
                  required
                />
              </div>
            </div>
          </div>

          <div className="crear-reporte-col">
            <div className="card">
              <div className="form-field">
                <label htmlFor="ubicacion">
                  Ubicación del incidente <span className="required">*</span>
                </label>
                <input
                  id="ubicacion"
                  type="text"
                  placeholder="Ej. Av. Tecnológico y Plutarco Elías Calles"
                  value={form.ubicacion}
                  onChange={updateField('ubicacion')}
                  required
                />
              </div>

              <label className="checkbox-field">
                <input type="checkbox" checked={useMyLocation} onChange={handleToggleMyLocation} />
                Usar mi ubicación actual
              </label>

              <div ref={mapContainerRef} className="map-container" />
              <p className="field-hint">
                {locatingAddress
                  ? 'Buscando dirección...'
                  : pinPlaced
                    ? 'Arrastra el pin para ajustar la ubicación exacta.'
                    : 'Haz clic en el mapa para colocar el pin del incidente.'}
              </p>
            </div>

            <div className="card">
              <label className="form-field-label">Evidencia fotográfica</label>
              <div
                className={`dropzone${dragActive ? ' active' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                role="button"
                tabIndex={0}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png"
                  hidden
                  onChange={handleFileInputChange}
                />

                {imagePreview ? (
                  <div className="image-preview-wrap">
                    <img src={imagePreview.url} alt={imagePreview.name} className="image-preview" />
                    <button type="button" className="image-remove-btn" onClick={handleRemoveImage} aria-label="Quitar imagen">
                      ×
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="dropzone-icon">
                      <UploadIcon />
                    </span>
                    <strong>Arrastra o selecciona una imagen</strong>
                    <span>JPG / PNG · máx. {MAX_IMAGE_MB} MB</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="crear-reporte-actions">
          <button type="button" className="btn btn-secondary" onClick={handleDiscard}>
            Descartar
          </button>
          <button type="submit" className="btn btn-primary">
            Enviar reporte
            <ArrowRightIcon />
          </button>
        </div>
      </form>
    </div>
  );
}

export default CrearReporte;
