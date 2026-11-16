# -*- coding: utf-8 -*-
"""
Pruebas Sprint 5 (PB-10: cubicacion y cotizacion automatica).
Se ejecuta sobre una copia limpia del proyecto con SQLite propio
(mismo patron que test_sprint4.py).
"""
import os
import shutil
import sys
import tempfile

ORIGEN = os.environ.get(
    'ASPLOT_ORIGEN', r'C:\Users\L\Desktop\Programa Asplot\Programa Asplot')
DESTINO = os.path.join(tempfile.gettempdir(), 'asplot_sprint5_test')

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

from app import create_app                              # noqa: E402
from models import (db, Usuario, Cliente, Proyecto,      # noqa: E402
                    TipoPlano, Plano, Inventario, Material)
import cotizador_auto                                    # noqa: E402

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
# Fixtures de archivos
# ---------------------------------------------------------------------------
CARPETA_PLANOS = os.path.join(DESTINO, 'static', 'uploads', 'planos')
CARPETA_SOLICITUDES = os.path.join(CARPETA_PLANOS, 'solicitudes')
os.makedirs(CARPETA_SOLICITUDES, exist_ok=True)


def crear_pdf(ruta, paginas):
    from pypdf import PdfWriter
    writer = PdfWriter()
    for ancho, alto in paginas:
        writer.add_blank_page(width=ancho, height=alto)
    with open(ruta, 'wb') as archivo:
        writer.write(archivo)


DXF = '''0
SECTION
2
HEADER
9
$INSUNITS
70
{unidades}
9
$EXTMIN
10
0.0
20
0.0
30
0.0
9
$EXTMAX
10
{maxx}
20
{maxy}
30
0.0
0
ENDSEC
0
EOF
'''


def crear_dxf(ruta, unidades=4, maxx=2000.0, maxy=1000.0):
    with open(ruta, 'w', encoding='utf-8') as archivo:
        archivo.write(DXF.format(unidades=unidades, maxx=maxx, maxy=maxy))


crear_pdf(os.path.join(CARPETA_SOLICITUDES, 'solicitud_a4.pdf'), [(595, 842)])
crear_dxf(os.path.join(CARPETA_PLANOS, 'plano_2000x1000.dxf'))
crear_pdf(os.path.join(CARPETA_PLANOS, 'plano_a0.pdf'),
          [(2384, 3370), (2384, 3370)])
with open(os.path.join(CARPETA_PLANOS, 'plano_reciente.dwg'), 'wb') as archivo:
    archivo.write(b'AC1032' + b'\x00' * 40)

# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------
with app.app_context():
    admin = Usuario.query.filter_by(email='admin@asplot.com').first()
    admin.set_password('admin123')

    usuario_cli = Usuario(nombre_usuario='cliente5', email='cli5@test.com',
                          rol='cliente', nombre_completo='Cliente Cinco',
                          activo=True)
    usuario_cli.set_password('cliente123')
    db.session.add(usuario_cli)
    db.session.flush()

    cliente = Cliente(nombre='Cliente', apellido='Cinco', email='cli5@test.com',
                      telefono='04140000005', direccion='Maturin',
                      id_usuario=usuario_cli.id_usuario)
    db.session.add(cliente)
    db.session.flush()

    tipo = TipoPlano.query.first()
    if tipo is None:
        tipo = TipoPlano(nombre_tipo='Plano arquitectonico')
        db.session.add(tipo)
        db.session.flush()

    def nuevo_proyecto(nombre, archivo_solicitud=None):
        proyecto = Proyecto(
            id_cliente=cliente.id_cliente, nombre_proyecto=nombre,
            descripcion='Proyecto de prueba Sprint 5', tipo_servicio='plano',
            estado='solicitado', archivo_solicitud=archivo_solicitud)
        db.session.add(proyecto)
        db.session.flush()
        return proyecto

    proyecto_pdf = nuevo_proyecto('Proyecto PDF A4', 'solicitud_a4.pdf')
    proyecto_dxf = nuevo_proyecto('Proyecto DXF')
    db.session.add(Plano(id_proyecto=proyecto_dxf.id_proyecto,
                         id_tipo_plano=tipo.id_tipo_plano,
                         id_usuario=admin.id_usuario,
                         nombre_plano='Plano 2000x1000',
                         archivo='plano_2000x1000.dxf'))
    proyecto_vacio = nuevo_proyecto('Proyecto sin archivos')
    proyecto_dwg = nuevo_proyecto('Proyecto DWG + PDF', 'solicitud_a4.pdf')
    db.session.add(Plano(id_proyecto=proyecto_dwg.id_proyecto,
                         id_tipo_plano=tipo.id_tipo_plano,
                         id_usuario=admin.id_usuario,
                         nombre_plano='Plano en DWG',
                         archivo='plano_reciente.dwg'))
    proyecto_a0 = nuevo_proyecto('Proyecto A0 doble')
    db.session.add(Plano(id_proyecto=proyecto_a0.id_proyecto,
                         id_tipo_plano=tipo.id_tipo_plano,
                         id_usuario=admin.id_usuario,
                         nombre_plano='Plano A0 dos paginas',
                         archivo='plano_a0.pdf'))
    db.session.commit()

    ID_PDF = proyecto_pdf.id_proyecto
    ID_DXF = proyecto_dxf.id_proyecto
    ID_VACIO = proyecto_vacio.id_proyecto
    ID_DWG = proyecto_dwg.id_proyecto
    ID_A0 = proyecto_a0.id_proyecto
    ID_ADMIN = admin.id_usuario

# ---------------------------------------------------------------------------
# 1-8: modulo de analisis (unitario)
# ---------------------------------------------------------------------------
ruta_a4 = os.path.join(CARPETA_SOLICITUDES, 'solicitud_a4.pdf')
r = cotizador_auto.analizar_archivo(ruta_a4)
check('1. PDF A4 -> area 0.0624 m2', r['ok'] and abs(r['area_m2'] - 0.0624) < 0.0005, r)
check('1b. PDF A4 detecta formato', r.get('formato_iso') == 'A4', r.get('detalle_area'))

r = cotizador_auto.analizar_archivo(os.path.join(CARPETA_PLANOS, 'plano_a0.pdf'))
check('2. PDF A0 x2 -> area 2.0 m2', r['ok'] and abs(r['area_m2'] - 2.0) < 0.01
      and r['paginas'] == 2, r)

ruta_roto = os.path.join(DESTINO, 'roto.pdf')
with open(ruta_roto, 'wb') as archivo:
    archivo.write(b'esto no es un pdf')
r = cotizador_auto.analizar_archivo(ruta_roto)
check('3. PDF corrupto -> ok:false con mensaje', not r['ok'] and r['mensaje'], r)

r = cotizador_auto.analizar_archivo(os.path.join(CARPETA_PLANOS, 'plano_2000x1000.dxf'))
check('4. DXF mm 2000x1000 -> 2.0 m2', r['ok'] and abs(r['area_m2'] - 2.0) < 0.0001, r)

ruta_m = os.path.join(DESTINO, 'metros.dxf')
crear_dxf(ruta_m, unidades=6, maxx=2.0, maxy=1.0)
r = cotizador_auto.analizar_archivo(ruta_m)
check('5. DXF en metros -> 2.0 m2', r['ok'] and abs(r['area_m2'] - 2.0) < 0.0001, r)

ruta_sin_u = os.path.join(DESTINO, 'sin_unidades.dxf')
crear_dxf(ruta_sin_u, unidades=0, maxx=2000.0, maxy=1000.0)
r = cotizador_auto.analizar_archivo(ruta_sin_u)
check('6. DXF sin unidades -> asume mm + advertencia',
      r['ok'] and abs(r['area_m2'] - 2.0) < 0.0001
      and any('milimetros' in a for a in r['advertencias']), r)

ruta_sin_ext = os.path.join(DESTINO, 'sin_extensiones.dxf')
with open(ruta_sin_ext, 'w', encoding='utf-8') as archivo:
    archivo.write('0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n')
r = cotizador_auto.analizar_archivo(ruta_sin_ext)
check('7. DXF sin extensiones -> ok:false', not r['ok'] and r['mensaje'], r)

ruta_bin = os.path.join(DESTINO, 'binario.dxf')
with open(ruta_bin, 'wb') as archivo:
    archivo.write(b'AutoCAD Binary DXF\r\n\x1a\x00' + b'\x00' * 10)
r = cotizador_auto.analizar_archivo(ruta_bin)
check('8. DXF binario -> ok:false', not r['ok'] and 'binario' in r['mensaje'], r)

# ---------------------------------------------------------------------------
# 9-16: endpoint en la app
# ---------------------------------------------------------------------------
admin_cli = app.test_client()
admin_cli.post('/login', data={'email': 'admin@asplot.com', 'password': 'admin123'})

r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_PDF)
datos = r.get_json() or {}
check('9. Endpoint PDF A4 responde 200 + ok',
      r.status_code == 200 and datos.get('ok') is True, datos)
if datos.get('ok'):
    a = datos['analisis']
    d = datos['desglose']
    esperado_base = round(a['area_m2'] * app.config['COTIZACION_TARIFA_M2'], 2)
    esperado_total = round(d['base'] + d['subtotal_insumos'] + d['margen'], 2)
    check('9b. Aritmetica base/total exacta',
          d['base'] == esperado_base and d['total'] == esperado_total
          and d['margen'] == round((d['base'] + d['subtotal_insumos'])
                                   * app.config['COTIZACION_MARGEN_PCT'] / 100, 2), d)
    check('9c. Usa el material A4 de la tabla materiales',
          d['insumos'] and 'A4' in d['insumos'][0]['nombre'], d['insumos'][0])
    check('16. texto_notas incluye area y total',
          'Area de impresion' in datos['texto_notas']
          and 'Total sugerido' in datos['texto_notas'])

r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_DXF)
datos = r.get_json() or {}
check('10. Endpoint DXF analiza el plano subido',
      r.status_code == 200 and datos.get('ok') is True
      and abs(datos['analisis']['area_m2'] - 2.0) < 0.0001, datos)

r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_VACIO)
datos = r.get_json() or {}
check('11. Proyecto sin archivos -> mensaje claro',
      r.status_code == 200 and datos.get('ok') is False
      and 'plano' in (datos.get('mensaje') or '').lower(), datos)

r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_DWG)
datos = r.get_json() or {}
check('12. DWG reciente + PDF adjunto -> usa el PDF',
      r.status_code == 200 and datos.get('ok') is True
      and str(datos.get('archivo')).endswith('.pdf'), datos.get('archivo'))

with app.app_context():
    antes = Proyecto.query.get(ID_PDF)
    estado_antes, presupuesto_antes = antes.estado, antes.presupuesto
r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_PDF)
with app.app_context():
    despues = Proyecto.query.get(ID_PDF)
    check('13. El calculo no escribe presupuesto ni estado',
          estado_antes == despues.estado
          and presupuesto_antes == despues.presupuesto,
          (estado_antes, presupuesto_antes, despues.estado, despues.presupuesto))

cli_cli = app.test_client()
cli_cli.post('/login', data={'email': 'cli5@test.com', 'password': 'cliente123'})
r = cli_cli.post('/proyectos/%d/cotizacion-automatica' % ID_PDF)
check('14. Cliente autenticado -> 403', r.status_code == 403, r.status_code)
anon = app.test_client()
r = anon.post('/proyectos/%d/cotizacion-automatica' % ID_PDF)
check('14b. Sin sesion -> redirige a login', r.status_code == 302
      and '/login' in r.headers.get('Location', ''), r.status_code)

with app.app_context():
    tinta = Material.query.filter_by(categoria='tinta').first()
    inv = Inventario.query.filter_by(id_material=tinta.id_material).first()
    stock_original = inv.cantidad
    ID_TINTA = tinta.id_material
    inv.cantidad = 0
    db.session.commit()
r = admin_cli.post('/proyectos/%d/cotizacion-automatica' % ID_A0)
datos = r.get_json() or {}
check('15. Stock insuficiente se marca alcanza:false',
      datos.get('ok') is True
      and any(i['alcanza'] is False for i in datos['desglose']['insumos']),
      datos.get('desglose', {}).get('insumos'))
with app.app_context():
    inv = Inventario.query.filter_by(id_material=ID_TINTA).first()
    inv.cantidad = stock_original
    db.session.commit()

# Formulario con auto=1 (bandeja) y boton presente
r = admin_cli.get('/proyectos/%d/aprobar?auto=1' % ID_PDF)
html = r.get_data(as_text=True)
check('17. Formulario muestra boton y dispara auto=1',
      r.status_code == 200 and 'btn-calcular' in html and 'calcular();' in html)

# ---------------------------------------------------------------------------
# Smoke de regresion Sprints 1-4
# ---------------------------------------------------------------------------
r = anon.get('/')
check('R1. Landing 200', r.status_code == 200)
r = anon.get('/solicitud')
check('R2. Formulario publico 200', r.status_code == 200
      and 'name="sitio_web"' in r.get_data(as_text=True))
r = admin_cli.get('/dashboard')
check('R3. Dashboard admin 200', r.status_code == 200)
r = admin_cli.get('/solicitudes')
check('R4. Bandeja de solicitudes 200', r.status_code == 200)
r = admin_cli.get('/inventario')
check('R5. Inventario 200', r.status_code == 200)

# ---------------------------------------------------------------------------
print()
if FALLOS:
    print('RESULTADO: %d FALLOS' % len(FALLOS))
    for fallo in FALLOS:
        print(' -', fallo)
    sys.exit(1)
print('RESULTADO: TODAS LAS PRUEBAS EN VERDE')
