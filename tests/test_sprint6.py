# -*- coding: utf-8 -*-
"""
Pruebas Sprint 6 (PB-11 inventario predictivo + PB-13 calidad de planos).
Copia limpia del proyecto con SQLite propio (patron de sprints anteriores).
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib
from datetime import date, datetime, timedelta

ORIGEN = os.environ.get(
    'ASPLOT_ORIGEN', r'C:\Users\L\Desktop\Programa Asplot\Programa Asplot')
DESTINO = os.path.join(tempfile.gettempdir(), 'asplot_sprint6_test')

IGNORAR = shutil.ignore_patterns(
    'venv', '.venv', '__pycache__', 'instance', '*.pyc', 'migracion',
    '.git', '.harness-memory', '.opencode', 'specs'
)

if os.path.exists(DESTINO):
    shutil.rmtree(DESTINO)
shutil.copytree(ORIGEN, DESTINO, ignore=IGNORAR)
os.makedirs(os.path.join(DESTINO, 'instance'), exist_ok=True)
os.chdir(DESTINO)
sys.path.insert(0, DESTINO)

from app import create_app                                   # noqa: E402
from models import (db, Usuario, Cliente, Proyecto, TipoPlano,  # noqa: E402
                    Material, Inventario, Factura, DetalleFactura, Plano)
import calidad_planos                                        # noqa: E402
import inventario_predictivo                                 # noqa: E402

app = create_app()
app.config['TESTING'] = True

FALLOS = []


def check(nombre, cond, detalle=''):
    if cond:
        print('OK   ', nombre)
    else:
        FALLOS.append(nombre)
        print('FALLO', nombre, detalle)


# ---------------------------------------------------------------------------
# Fixtures de imagen (sin Pillow)
# ---------------------------------------------------------------------------
TMP = os.path.join(DESTINO, 'fixtures_calidad')
os.makedirs(TMP, exist_ok=True)


def crear_png(nombre, ppu=None):
    def chunk(tipo, datos):
        return (struct.pack('>I', len(datos)) + tipo + datos
                + struct.pack('>I', zlib.crc32(tipo + datos) & 0xffffffff))
    ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    contenido = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
    if ppu:
        contenido += chunk(b'pHYs', struct.pack('>IIB', ppu, ppu, 1))
    contenido += chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00'))
    contenido += chunk(b'IEND', b'')
    ruta = os.path.join(TMP, nombre)
    with open(ruta, 'wb') as archivo:
        archivo.write(contenido)
    return ruta


def crear_jpg(nombre, dpi=300):
    app0 = (b'JFIF\x00' + b'\x01\x01' + b'\x01'
            + struct.pack('>H', dpi) + struct.pack('>H', dpi) + b'\x00\x00')
    datos = b'\xff\xd8' + b'\xff\xe0' + struct.pack('>H', len(app0) + 2) + app0 + b'\xff\xd9'
    ruta = os.path.join(TMP, nombre)
    with open(ruta, 'wb') as archivo:
        archivo.write(datos)
    return ruta


def estado(items, clave):
    return next(i['estado'] for i in items if i['clave'] == clave)


buena_png = crear_png('buena.png', ppu=11811)     # 300 dpi
baja_png = crear_png('baja.png', ppu=2835)        # 72 dpi
sin_dpi_png = crear_png('sin_dpi.png')
buena_jpg = crear_jpg('buena.jpg', dpi=300)
renombrada = os.path.join(TMP, 'renombrada.pdf')
with open(renombrada, 'wb') as archivo:
    archivo.write(b'\xff\xd8\xff\xe0' + b'\x00' * 40)
roto_pdf = os.path.join(TMP, 'roto.pdf')
with open(roto_pdf, 'wb') as archivo:
    archivo.write(b'%PDF-1.4 basura sin estructura')
vacio = os.path.join(TMP, 'vacio.pdf')
with open(vacio, 'wb'):
    pass
from pypdf import PdfWriter                              # noqa: E402
writer = PdfWriter()
writer.add_blank_page(width=595, height=842)
a4_pdf = os.path.join(TMP, 'a4.pdf')
with open(a4_pdf, 'wb') as archivo:
    writer.write(archivo)

# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------
with app.app_context():
    admin = Usuario.query.filter_by(email='admin@asplot.com').first()
    admin.set_password('admin123')

    usuario_cli = Usuario(nombre_usuario='cliente6', email='cli6@test.com',
                          rol='cliente', nombre_completo='Cliente Seis',
                          activo=True)
    usuario_cli.set_password('cliente123')
    db.session.add(usuario_cli)
    db.session.flush()

    cliente = Cliente(nombre='Cliente', apellido='Seis', email='cli6@test.com',
                      telefono='04140000006', direccion='Maturin',
                      id_usuario=usuario_cli.id_usuario)
    db.session.add(cliente)
    db.session.flush()

    tipo = TipoPlano.query.first()
    proyecto = Proyecto(id_cliente=cliente.id_cliente,
                        nombre_proyecto='Proyecto Calidad',
                        descripcion='Pruebas de calidad de planos',
                        tipo_servicio='plano', estado='solicitado')
    db.session.add(proyecto)
    db.session.flush()

    papel_a0 = Material.query.filter_by(subcategoria='A0').first()
    tinta = Material.query.filter_by(categoria='tinta').first()

    hoy = datetime.now()
    for dias, cantidad in ((29, 10), (10, 10), (0, 10)):
        factura = Factura(id_proyecto=proyecto.id_proyecto,
                          id_cliente=cliente.id_cliente,
                          id_usuario=admin.id_usuario,
                          total=cantidad * 10,
                          fecha_factura=hoy - timedelta(days=dias))
        db.session.add(factura)
        db.session.flush()
        db.session.add(DetalleFactura(id_factura=factura.id_factura,
                                      id_material=papel_a0.id_material,
                                      descripcion='Consumo de prueba',
                                      cantidad=cantidad,
                                      precio_unitario=10))
    db.session.commit()

    ID_PROYECTO = proyecto.id_proyecto
    ID_CLIENTE = cliente.id_cliente
    ID_TIPO = tipo.id_tipo_plano
    ID_ADMIN = admin.id_usuario
    ID_PAPEL = papel_a0.id_material
    ID_TINTA = tinta.id_material

# ---------------------------------------------------------------------------
# 1-8: calidad de planos (unitario)
# ---------------------------------------------------------------------------
r = calidad_planos.verificar_archivo(buena_png)
check('1. PNG 300 dpi -> ok', estado(r, 'dpi') == 'ok' and estado(r, 'formato') == 'ok', r)
r = calidad_planos.verificar_archivo(baja_png)
check('2. PNG 72 dpi -> aviso', estado(r, 'dpi') == 'aviso', r)
r = calidad_planos.verificar_archivo(sin_dpi_png)
check('3. PNG sin pHYs -> no verificable', estado(r, 'dpi') == 'no_verificable', r)
r = calidad_planos.verificar_archivo(buena_jpg)
check('4. JPG 300 dpi -> ok', estado(r, 'dpi') == 'ok', r)
r = calidad_planos.verificar_archivo(renombrada)
check('5. JPG renombrado a PDF -> aviso de formato', estado(r, 'formato') == 'aviso', r)
r = calidad_planos.verificar_archivo(roto_pdf)
check('6. PDF corrupto -> aviso', estado(r, 'pagina') == 'aviso'
      or estado(r, 'legible') == 'aviso', r)
r = calidad_planos.verificar_archivo(vacio)
check('7. Archivo vacio -> aviso', estado(r, 'archivo') == 'aviso', r)
r = calidad_planos.verificar_archivo(a4_pdf)
check('8. PDF A4 -> pagina ok', estado(r, 'pagina') == 'ok', r)

# ---------------------------------------------------------------------------
# 9-11: subida no bloqueante y detalle
# ---------------------------------------------------------------------------
admin_cli = app.test_client()
admin_cli.post('/login', data={'email': 'admin@asplot.com', 'password': 'admin123'})

with open(baja_png, 'rb') as archivo:
    r = admin_cli.post('/planos/subir', data={
        'id_proyecto': str(ID_PROYECTO),
        'id_tipo_plano': str(ID_TIPO),
        'nombre_plano': 'Plano baja resolucion',
        'archivo': (archivo, 'baja.png'),
    }, content_type='multipart/form-data', follow_redirects=True)
html = r.get_data(as_text=True)
check('9. Subida con advertencia no bloquea (200 y guardado)',
      r.status_code == 200 and 'advertencias de calidad' in html
      and 'DPI' in html, r.status_code)

with app.app_context():
    plano = Plano.query.filter_by(nombre_plano='Plano baja resolucion').first()
    check('9b. El plano quedo registrado', plano is not None)
    ID_PLANO = plano.id_plano if plano else 0

r = admin_cli.get('/planos/detalle/%d' % ID_PLANO)
html = r.get_data(as_text=True)
check('10. Detalle muestra checklist de calidad',
      r.status_code == 200 and 'Calidad del archivo' in html
      and 'Resolución (DPI)' in html and 'aviso' in html)

r = admin_cli.get('/planos/detalle/999999')
check('11. Plano inexistente -> 404 controlado', r.status_code == 404)

# ---------------------------------------------------------------------------
# 12-15: inventario predictivo
# ---------------------------------------------------------------------------
with app.app_context():
    materiales = []
    existencias = {i.id_material: i.cantidad for i in Inventario.query.all()}
    for material in Material.query.filter_by(activo=True).all():
        materiales.append({
            'id': material.id_material,
            'nombre': material.nombre_material,
            'stock': existencias.get(material.id_material, 0),
            'stock_minimo': material.stock_minimo or 0,
            'unidad': material.unidad_medida,
        })
    consumos = {
        ID_PAPEL: {'total': 30.0, 'primera': hoy - timedelta(days=29)},
    }
    params = {'ventana_dias': 90, 'dias_reposicion': 7, 'dias_seguridad': 7,
              'dias_compra': 30, 'factor_activo': 0.10, 'tope_activo': 0.50}
    predicciones = inventario_predictivo.calcular_predicciones(
        materiales, consumos, 0, params, hoy.date())
    papel = next(p for p in predicciones if p['id_material'] == ID_PAPEL)
    check('12. Velocidad 1.0 u/dia y 12 dias restantes',
          papel['velocidad'] == 1.0 and papel['dias_restantes'] == 12.0, papel)
    check('12b. Punto de reorden 14 y compra 18',
          papel['punto_reorden'] == 14.0 and papel['compra_sugerida'] == 18
          and papel['estado'] == 'riesgo', papel)
    otro = next(p for p in predicciones if p['id_material'] != ID_PAPEL)
    check('13. Material sin consumo -> sin_historial', otro['estado'] == 'sin_historial', otro)

r = admin_cli.get('/inventario')
html = r.get_data(as_text=True)
check('14. Panel de prediccion visible con datos',
      r.status_code == 200 and 'Predicción de reabastecimiento' in html
      and 'Papel Bond A0' in html and '1.00' in html)

# Ajuste por proyecto en progreso
with app.app_context():
    activo = Proyecto(id_cliente=ID_CLIENTE,
                      nombre_proyecto='Proyecto activo', descripcion='x',
                      tipo_servicio='plano', estado='en_progreso')
    db.session.add(activo)
    db.session.commit()
r = admin_cli.get('/inventario')
html = r.get_data(as_text=True)
check('15. Ajuste por proyecto en progreso (x1.10)',
      'ajuste ×1.10' in html and '1.10' in html)

# ---------------------------------------------------------------------------
# 16-18: silenciar / reactivar / RBAC
# ---------------------------------------------------------------------------
ruta_json = os.path.join(app.instance_path, 'inventario_alertas.json')
r = admin_cli.post('/inventario/alertas/silenciar/%d' % ID_PAPEL)
check('16. Silenciar alerta -> 302', r.status_code == 302)
check('16b. JSON de silencios creado', os.path.isfile(ruta_json))
r = admin_cli.get('/inventario')
html = r.get_data(as_text=True)
check('16c. El material aparece como silenciada',
      'Silenciada hasta' in html)
with app.app_context():
    from datetime import date as _date
    silencios = inventario_predictivo.leer_silencios(ruta_json, _date.today())
check('16d. Silencio persistido para el material', ID_PAPEL in silencios, silencios)

cli_cli = app.test_client()
cli_cli.post('/login', data={'email': 'cli6@test.com', 'password': 'cliente123'})
r = cli_cli.post('/inventario/alertas/silenciar/%d' % ID_TINTA)
check('17. Cliente no puede silenciar (302 con aviso)', r.status_code == 302)
with app.app_context():
    from datetime import date as _date
    silencios = inventario_predictivo.leer_silencios(ruta_json, _date.today())
check('17b. El cliente no escribio el silencio', ID_TINTA not in silencios, silencios)

r = admin_cli.post('/inventario/alertas/reactivar/%d' % ID_PAPEL)
r = admin_cli.get('/inventario')
html = r.get_data(as_text=True)
check('18. Reactivar devuelve el material a riesgo',
      r.status_code == 200 and 'Silenciada hasta' not in html and 'Riesgo' in html)

# ---------------------------------------------------------------------------
# Smoke de regresion
# ---------------------------------------------------------------------------
anon = app.test_client()
r = anon.get('/')
check('R1. Landing 200', r.status_code == 200)
r = anon.get('/solicitud')
check('R2. Solicitud publica 200', r.status_code == 200)
r = admin_cli.get('/dashboard')
check('R3. Dashboard 200', r.status_code == 200)
r = admin_cli.get('/planos')
check('R4. Planos 200', r.status_code == 200)
r = admin_cli.get('/facturas')
check('R5. Facturas 200', r.status_code == 200)
r = admin_cli.get('/clientes')
check('R6. Clientes 200', r.status_code == 200)

# ---------------------------------------------------------------------------
print()
if FALLOS:
    print('RESULTADO: %d FALLOS' % len(FALLOS))
    for fallo in FALLOS:
        print(' -', fallo)
    sys.exit(1)
print('RESULTADO: TODAS LAS PRUEBAS EN VERDE')
