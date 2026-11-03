import Icon from '../common/Icon';

/**
 * AvisoPrivacidadUbicacion: aviso previo a pedir el permiso de ubicación
 * (una de las dos alertas del producto). Solo si la persona pulsa "Permitir"
 * se llama a navigator.geolocation. No se recuerda la elección: se muestra
 * cada vez que se pulsa "Usar mi ubicación actual".
 */
function AvisoPrivacidadUbicacion({ onAceptar, onCancelar }) {
  return (
    <div className="ubi-aviso" role="dialog" aria-labelledby="ubi-aviso-titulo" aria-describedby="ubi-aviso-texto">
      <div className="ubi-aviso-titulo" id="ubi-aviso-titulo">
        <Icon name="nav" size={16} />
        Usar tu ubicación
      </div>
      <p className="ubi-aviso-texto" id="ubi-aviso-texto">
        Para colocar el pin usaremos la ubicación de tu dispositivo <b>una sola vez</b>. SARV solo guarda el
        punto que publiques con el reporte, no te sigue en tiempo real. Después tu navegador te pedirá permiso.
      </p>
      <div className="ubi-aviso-acciones">
        <button type="button" className="btn-outline" onClick={onCancelar}>
          Ahora no
        </button>
        <button type="button" className="btn-primary" onClick={onAceptar}>
          Permitir y continuar
        </button>
      </div>
    </div>
  );
}

export default AvisoPrivacidadUbicacion;
