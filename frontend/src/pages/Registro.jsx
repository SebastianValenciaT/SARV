import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/layout/Navbar';
import api from '../services/api';
import './Registro.css';

// Nombre legible de cada campo que puede traer errores el servidor
const CAMPOS = {
  email: 'Correo',
  password: 'Contraseña',
  nombre: 'Nombre',
  apellido: 'Apellido',
  aceptaPrivacidad: 'Aviso de privacidad',
};
const MIN_PASSWORD = 8; // mismo mínimo que el servidor (AUTH_PASSWORD_VALIDATORS)

// { email: ['Ya existe…'], password: ['…', '…'] } -> "Correo: Ya existe… Contraseña: … …"
function erroresDelServidor(data) {
  const partes = Object.entries(data ?? {}).map(([campo, mensajes]) => {
    const texto = [].concat(mensajes).join(' ');
    return CAMPOS[campo] ? `${CAMPOS[campo]}: ${texto}` : texto;
  });
  return partes.join(' ') || 'Ocurrió un error en el registro. Verifica tus datos.';
}

export default function Registro() {
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    correo: '',
    password: '',
    confirmPassword: '',
    aceptaPrivacidad: false
  });
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { nombre, apellido, correo, password, confirmPassword, aceptaPrivacidad } = formData;

    // Validaciones del frontend
    if (!nombre || !apellido || !correo || !password || !confirmPassword) {
      setError('Por favor, completa todos los campos obligatorios.');
      return;
    }
    if (password.length < MIN_PASSWORD) {
      setError(`La contraseña debe tener un mínimo de ${MIN_PASSWORD} caracteres.`);
      return;
    }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    if (!aceptaPrivacidad) {
      setError('Debes leer y aceptar el Aviso de Privacidad.');
      return;
    }

    // Petición al endpoint del backend (api.js ya conoce la dirección del servidor)
    try {
      // Mapeamos los datos del estado a lo que espera serializers.py
      await api.post('/registro/', {
        nombre: nombre,
        apellido: apellido,
        email: correo, // El backend espera 'email', pero tu estado se llama 'correo'
        password: password,
        aceptaPrivacidad: aceptaPrivacidad
      });

      // Redirige al login y le pasa un estado para mostrar el banner azul (HU-027)
      navigate('/login', { state: { message: '¡Cuenta creada exitosamente!' } });
    } catch (err) {
      const status = err.response?.status;
      if (status === 400) {
        // Muestra los errores por campo que devuelva el servidor, ya en español
        // (correo ya registrado, contraseña débil, privacidad...)
        setError(erroresDelServidor(err.response.data));
      } else if (status === 429) {
        setError('Se hicieron demasiados registros desde esta red. Intenta de nuevo más tarde.');
      } else if (!err.response) {
        setError('Error al conectar con el servidor. Verifica que el backend esté encendido.');
      } else {
        setError('Ocurrió un error en el registro. Verifica tus datos.');
      }
    }
  };

  return (
    <div className="registro-page">
      <Navbar />

      <main className="registro-content">
        {/* Panel Izquierdo: Imagen */}
        <div className="registro-left-panel"></div>

        {/* Panel Derecho: Formulario */}
        <div className="registro-right-panel">
          <div className="registro-form-container">
            <h1 className="registro-title">Llena los Campos para Crear tu Cuenta</h1>

            {error && <div className="registro-error-alert">{error}</div>}

            <form onSubmit={handleSubmit} className="registro-form">
              <div className="form-group">
                <label>Nombre <span className="asterisk">*</span></label>
                <input
                  type="text"
                  name="nombre"
                  value={formData.nombre}
                  onChange={handleChange}
                  className="registro-input"
                />
              </div>

              <div className="form-group">
                <label>Apellido <span className="asterisk">*</span></label>
                <input
                  type="text"
                  name="apellido"
                  value={formData.apellido}
                  onChange={handleChange}
                  className="registro-input"
                />
              </div>

              <div className="form-group">
                <label>Correo Electrónico <span className="asterisk">*</span></label>
                <input
                  type="email"
                  name="correo"
                  value={formData.correo}
                  onChange={handleChange}
                  className="registro-input"
                />
              </div>

              <div className="form-group">
                <label>Contraseña (Mínimo {MIN_PASSWORD} caracteres) <span className="asterisk">*</span></label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  className="registro-input"
                />
              </div>

              <div className="form-group">
                <label>Confirmar Contraseña <span className="asterisk">*</span></label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="registro-input"
                />
              </div>

              <div className="privacidad-wrapper">
                <input
                  type="checkbox"
                  name="aceptaPrivacidad"
                  id="aceptaPrivacidad"
                  checked={formData.aceptaPrivacidad}
                  onChange={handleChange}
                />
                <label htmlFor="aceptaPrivacidad">
                  He leído y aceptado el{' '}
                  <span className="link-privacidad" onClick={(e) => { e.preventDefault(); setShowModal(true); }}>
                    Aviso de privacidad.
                  </span>
                </label>
              </div>

              <button type="submit" className="btn-registro-submit">
                Registrarse
              </button>
            </form>
          </div>
        </div>
      </main>

      {/* Ventana Modal del Aviso de Privacidad */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2 className="modal-title">Aviso de Privacidad</h2>
            <p className="modal-text">
              SARV hará uso de tu nombre y apellido a la hora de la visualización de un reporte, esto con el fin de evitar entradas falsas por individuos inexistentes con el único fin de alentar a la desinformación.
            </p>
            <p className="modal-text">
              Así también como se solicitará el acceso a la ubicación de tu dispositivo a la hora de realizar un reporte, esto con el fin de obtener la ubicación del incidente de la manera más precisa para quienes consulten el reporte.
            </p>
            <button className="btn-modal-continuar" onClick={() => setShowModal(false)}>
              Continuar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}