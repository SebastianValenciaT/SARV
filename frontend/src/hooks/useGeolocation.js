import { useCallback, useState } from 'react';

const OPCIONES = { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 };

/**
 * useGeolocation: envuelve navigator.geolocation.
 *
 * estado: 'inactivo' | 'solicitando' | 'listo' | 'error' | 'denegado' | 'inseguro'
 * solicitar(): pide la ubicación UNA vez y devuelve una promesa con
 *   { ok: true, latitud, longitud, precision }  (precision en metros), o
 *   { ok: false, mensaje }                       (texto listo para mostrar).
 * Solo debe llamarse después de que la persona aceptó el aviso de privacidad.
 */
export function useGeolocation() {
  const [estado, setEstado] = useState('inactivo');
  const [posicion, setPosicion] = useState(null);
  const [error, setError] = useState(null);

  const fallar = useCallback((nuevoEstado, mensaje) => {
    setEstado(nuevoEstado);
    setError(mensaje);
    return { ok: false, mensaje };
  }, []);

  const solicitar = useCallback(() => {
    // El navegador solo da la ubicación en HTTPS o en localhost ("contexto seguro").
    if (window.isSecureContext === false) {
      return Promise.resolve(fallar(
        'inseguro',
        'La ubicación del dispositivo solo funciona en páginas seguras (HTTPS) o en localhost. '
          + 'Busca la dirección o toca el mapa para colocar el pin.',
      ));
    }
    if (!('geolocation' in navigator)) {
      return Promise.resolve(fallar('error', 'Tu navegador no permite obtener la ubicación.'));
    }

    setEstado('solicitando');
    setError(null);
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const nueva = {
            latitud: pos.coords.latitude,
            longitud: pos.coords.longitude,
            precision: pos.coords.accuracy,
          };
          setPosicion(nueva);
          setEstado('listo');
          resolve({ ok: true, ...nueva });
        },
        (err) => {
          if (err.code === err.PERMISSION_DENIED) {
            resolve(fallar(
              'denegado',
              'No diste permiso para usar tu ubicación. Puedes activarlo en los ajustes del navegador, '
                + 'o buscar la dirección y tocar el mapa.',
            ));
          } else if (err.code === err.TIMEOUT) {
            resolve(fallar('error', 'Obtener tu ubicación tardó demasiado. Intenta de nuevo o coloca el pin a mano.'));
          } else {
            resolve(fallar('error', 'No pudimos obtener tu ubicación. Coloca el pin a mano.'));
          }
        },
        OPCIONES,
      );
    });
  }, [fallar]);

  return { estado, posicion, error, solicitar };
}
