from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from usuarios.models import Usuario

from .models import Denuncia, Reaccion, Reporte, TipoIncidente
from .zonas import CENTRO_LAT, CENTRO_LNG, dentro_de_juarez, zona_de


class ZonaTests(TestCase):
    """Puntos de prueba para calibrar zona_de().

    Los casos relativos al centro validan la lógica. Para calibrar, agrega
    aquí ubicaciones reales (copia lat/lng desde openstreetmap.org) con la
    zona que el equipo espera.
    """

    def test_centro(self):
        self.assertEqual(zona_de(CENTRO_LAT, CENTRO_LNG), 'centro')
        self.assertEqual(zona_de(CENTRO_LAT + 0.01, CENTRO_LNG), 'centro')   # ~1.1 km

    def test_puntos_cardinales(self):
        self.assertEqual(zona_de(CENTRO_LAT + 0.05, CENTRO_LNG), 'norte')
        self.assertEqual(zona_de(CENTRO_LAT - 0.05, CENTRO_LNG), 'sur')
        self.assertEqual(zona_de(CENTRO_LAT, CENTRO_LNG + 0.08), 'oriente')
        self.assertEqual(zona_de(CENTRO_LAT, CENTRO_LNG - 0.08), 'poniente')

    def test_diagonal_gana_el_eje_mayor(self):
        self.assertEqual(zona_de(CENTRO_LAT - 0.03, CENTRO_LNG + 0.10), 'oriente')
        self.assertEqual(zona_de(CENTRO_LAT - 0.10, CENTRO_LNG + 0.03), 'sur')

    def test_limites_de_juarez(self):
        self.assertTrue(dentro_de_juarez(CENTRO_LAT, CENTRO_LNG))
        self.assertFalse(dentro_de_juarez(31.9, -106.4))     # al norte, en EE. UU.
        self.assertFalse(dentro_de_juarez(28.63, -106.07))   # Chihuahua capital


class BaseDatos(TestCase):
    def setUp(self):
        self.autor = Usuario.objects.create_user('autor@correo.mx', 'secreto1', nombre='Autor')
        self.otro = Usuario.objects.create_user('otro@correo.mx', 'secreto2', nombre='Otro')
        self.bache = TipoIncidente.objects.get(nombre='Bache')
        self.tipo_otro = TipoIncidente.objects.get(nombre='Otro')

    def crear_reporte(self, **extra):
        datos = dict(
            usuario=self.autor, tipo=self.bache, titulo='Bache profundo',
            descripcion='Bache profundo en el carril derecho', gravedad='moderado',
            direccion='Av. Tecnológico', latitud=f'{CENTRO_LAT + 0.05:.6f}', longitud=f'{CENTRO_LNG:.6f}',
            fecha_incidente=timezone.now() - timedelta(hours=1),
        )
        datos.update(extra)
        return Reporte.objects.create(**datos)


class CatalogoYUsuarioTests(BaseDatos):
    def test_seed_de_tipos(self):
        self.assertEqual(
            set(TipoIncidente.objects.values_list('nombre', flat=True)),
            {'Bache', 'Choque', 'Inundación', 'Tráfico', 'Obstrucción', 'Otro'},
        )

    def test_password_con_hash_y_correo_unico(self):
        self.assertNotEqual(self.autor.password, 'secreto1')
        self.assertTrue(self.autor.check_password('secreto1'))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Usuario.objects.create_user('autor@correo.mx', 'x1y2z3', nombre='Dup')


class ReporteTests(BaseDatos):
    def test_valores_automaticos(self):
        r = self.crear_reporte()
        self.assertEqual(r.estado, 'sin_resolver')
        self.assertEqual(r.zona, 'norte')
        self.assertIsNotNone(r.creado_en)
        self.assertIsNone(r.resuelto_en)
        self.assertTrue(r.es_editable)

    def test_zona_se_recalcula_al_cambiar_ubicacion(self):
        r = self.crear_reporte()
        r.latitud = f'{CENTRO_LAT - 0.05:.6f}'
        r.save()
        self.assertEqual(r.zona, 'sur')

    def test_resolver_es_de_un_solo_sentido(self):
        r = self.crear_reporte()
        r.resolver()
        r.refresh_from_db()
        self.assertEqual(r.estado, 'resuelto')
        self.assertIsNotNone(r.resuelto_en)
        self.assertEqual(r.zona, 'norte')
        self.assertFalse(r.es_editable)
        primera = r.resuelto_en
        r.resolver()
        r.refresh_from_db()
        self.assertEqual(r.resuelto_en, primera)

    def test_ubicacion_fuera_de_juarez_se_rechaza(self):
        r = self.crear_reporte(latitud='31.900000')
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_descripcion_entre_10_y_500(self):
        with self.assertRaises(ValidationError):
            self.crear_reporte(descripcion='corta').full_clean()
        with self.assertRaises(ValidationError):
            self.crear_reporte(descripcion='x' * 501).full_clean()

    def test_tipo_otro_exige_descripcion_y_la_muestra(self):
        sin = self.crear_reporte(tipo=self.tipo_otro, tipo_otro='')
        with self.assertRaises(ValidationError):
            sin.full_clean()
        con = self.crear_reporte(tipo=self.tipo_otro, tipo_otro='Semáforo descompuesto')
        con.full_clean()
        self.assertEqual(con.tipo_etiqueta, 'Semáforo descompuesto')

    def test_tipo_normal_ignora_tipo_otro(self):
        r = self.crear_reporte(tipo_otro='texto suelto')
        self.assertEqual(r.tipo_otro, '')
        self.assertEqual(r.tipo_etiqueta, 'Bache')


class ReaccionDenunciaTests(BaseDatos):
    def test_una_reaccion_por_usuario_y_reporte(self):
        r = self.crear_reporte()
        Reaccion.objects.create(reporte=r, usuario=self.otro, tipo='resuelto')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reaccion.objects.create(reporte=r, usuario=self.otro, tipo='sin_resolver')
        self.assertEqual(r.reacciones.count(), 1)

    def test_una_denuncia_por_usuario_y_reporte(self):
        r = self.crear_reporte()
        Denuncia.objects.create(reporte=r, usuario=self.otro, motivo='Parece un reporte falso')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Denuncia.objects.create(reporte=r, usuario=self.otro, motivo='Otra vez el mismo reporte')

    def test_borrar_reporte_borra_sus_dependencias(self):
        r = self.crear_reporte()
        Reaccion.objects.create(reporte=r, usuario=self.otro, tipo='resuelto')
        Denuncia.objects.create(reporte=r, usuario=self.otro, motivo='Parece un reporte falso')
        r.delete()
        self.assertEqual(Reaccion.objects.count(), 0)
        self.assertEqual(Denuncia.objects.count(), 0)
