# -*- coding: utf-8 -*-
"""
Pruebas Sprint 7 (PB-12 copilot administrativo NL -> SQL).
Copia limpia del proyecto con SQLite propio (patron de sprints anteriores).

Cubre: validador SQL, 8 plantillas sin API, coincidencia por texto libre,
fallback del LLM (SQL rechazado y error de red), RBAC, log de auditoria
y navegacion (sidebar/dashboard).
"""
import logging
import os
import shutil
import sys
import tempfile
from datetime import date, datetime

ORIGEN = os.environ.get(
    'ASPLOT_ORIGEN', r'C:\Users\L\Desktop\Programa Asplot\Programa Asplot')
DESTINO = os.path.join(tempfile.gettempdir(), 'asplot_sprint7_test')

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
                    Plano, Material, Inventario, Factura, DetalleFactura)
import copilot                                               # noqa: E402

app = create_app()
app.config['TESTING'] = True
app.config['COPILOT_API_KEY'] = None  # modo plantillas por defecto

FALLOS = []


def check(nombre, cond, detalle=''):
    if cond:
        print('OK   ', nombre)
    else:
        FALLOS.append(nombre)
        print('FALLO', nombre, detalle)


# ---------------------------------------------------------------------------
# Datos de prueba: facturas del mes, proyecto solicitado, inventario bajo
# ---------------------------------------------------------------------------
with app.app_context():
    admin = Usuario.query.filter_by(email='admin@asplot.com').first()
    admin.set_password('admin123')

    usuario_cli = Usuario(nombre_usuario='cliente7', email='cli7@test.com',
                           rol='cliente', nombre_completo='Cliente Siete',
                           activo=True)
    usuario_cli.set_password('cliente123')
    db.session.add(usuario_cli)
    db.session.flush()

    cliente = Cliente(nombre='Cliente', apellido='Siete',
                       email='cli7@test.com', telefono='04140000007',
                       direccion='Maturin', id_usuario=usuario_cli.id_usuario)
    db.session.add(cliente)
    db.session.flush()

    rollo = Material(nombre_material='Rollo prueba A1', categoria='papel',
                     subcategoria='A1', precio_unitario=2.5,
                     precio_compra=1.2, unidad_medida='metro',
                     stock_minimo=10, activo=True)
    db.session.add(rollo)
    db.session.flush()
    db.session.add(Inventario(id_material=rollo.id_material, cantidad=4,
                               ubicacion='Estante A'))  # bajo minimo 10

    p1 = Proyecto(id_cliente=cliente.id_cliente,
                  nombre_proyecto='Plano vivienda prueba',
                  descripcion='Plano de prueba', tipo_servicio='plano',
                  estado='ejecutado', presupuesto=100)
    p2 = Proyecto(id_cliente=cliente.id_cliente,
                  nombre_proyecto='Solicitud pendiente prueba',
                  descripcion='Pendiente', tipo_servicio='correccion',
                  estado='solicitado')
    db.session.add_all([p1, p2])
    db.session.flush()

    tipo_plano = TipoPlano(nombre_tipo='Arquitectonico prueba',
                            descripcion='Tipo de prueba')
    db.session.add(tipo_plano)
    db.session.flush()
    plano = Plano(id_proyecto=p1.id_proyecto, id_tipo_plano=tipo_plano.id_tipo_plano,
                  id_usuario=admin.id_usuario, nombre_plano='Plano prueba',
                  archivo='plano_prueba.pdf')
    db.session.add(plano)
    db.session.flush()

    hoy = date.today()
    factura = Factura(id_proyecto=p1.id_proyecto, id_cliente=cliente.id_cliente,
                      id_usuario=admin.id_usuario, subtotal=25.0, impuesto=0.0,
                      descuento=0.0, total=25.0, estado_pago='pagada',
                      fecha_factura=datetime(hoy.year, hoy.month, 2, 12, 0))
    db.session.add(factura)
    db.session.flush()
    db.session.add(DetalleFactura(id_factura=factura.id_factura,
                                  id_plano=plano.id_plano,
                                  id_material=rollo.id_material,
                                  descripcion='Impresion A1', cantidad=10,
                                  precio_unitario=2.5, descuento=0.0))
    db.session.commit()

# ---------------------------------------------------------------------------
# 1. Validador de SQL
# ---------------------------------------------------------------------------
ok, envuelto, error = copilot.validar_sql('SELECT * FROM facturas', 100)
check('V1. acepta SELECT y agrega LIMIT', ok and 'LIMIT 100' in envuelto,
      error)

ok, _, error = copilot.validar_sql(
    'WITH x AS (SELECT 1 AS n) SELECT n FROM x', 100)
check('V2. acepta WITH (CTE como alias local)', ok, error)

ok, _, error = copilot.validar_sql(
    'WITH u AS (SELECT 1) SELECT * FROM facturas JOIN u ON 1=1', 100)
check('V3. CTE no libera tablas prohibidas... y facturas si pasa', ok, error)

for sql_malo, nombre in [
    ('DROP TABLE facturas', 'V4. rechaza DROP'),
    ('DELETE FROM facturas WHERE 1=1', 'V5. rechaza DELETE'),
    ('SELECT * FROM usuarios', 'V6. rechaza tabla usuarios'),
    ('SELECT 1; DROP TABLE facturas', 'V7. rechaza sentencia multiple'),
    ('SELECT 1 -- comentario', 'V8. rechaza comentario --'),
    ('SELECT * FROM facturas; UPDATE materiales SET precio=0',
     'V9. rechaza UPDATE tras punto y coma'),
    ("SELECT 'x' INTO OUTFILE '/tmp/x' FROM facturas", 'V10. rechaza OUTFILE'),
    ('', 'V11. rechaza consulta vacia'),
]:
    ok, _, error = copilot.validar_sql(sql_malo, 100)
    check(nombre, not ok, error)

for plantilla in copilot.PLANTILLAS:
    sql, params = plantilla['consulta'](date.today())
    ok, _, error = copilot.validar_sql(sql, 200)
    check('V12. plantilla pre-validada: %s' % plantilla['id'], ok, error)

# ---------------------------------------------------------------------------
# 2. Resolucion de plantillas por texto libre
# ---------------------------------------------------------------------------
p = copilot.resolver_plantilla('¿Cuál fue la facturación de este mes?')
check('R1. texto libre -> facturacion_mes',
      p is not None and p['id'] == 'facturacion_mes', p and p['id'])

p = copilot.resolver_plantilla('que materiales estan por debajo del minimo')
check('R2. texto libre -> inventario_riesgo',
      p is not None and p['id'] == 'inventario_riesgo', p and p['id'])

p = copilot.resolver_plantilla('hola mundo xylophone')
check('R3. texto sin coincidencia -> None', p is None, p and p['id'])

# ---------------------------------------------------------------------------
# 3. RBAC
# ---------------------------------------------------------------------------
anonimo = app.test_client()
r = anonimo.get('/copilot', follow_redirects=False)
check('A1. anonimo redirige a login', r.status_code == 302, r.status_code)

cliente_cli = app.test_client()
cliente_cli.post('/login', data={'email': 'cli7@test.com',
                                 'password': 'cliente123'})
r = cliente_cli.get('/copilot', follow_redirects=False)
check('A2. cliente redirige al dashboard', r.status_code == 302
      and '/dashboard' in r.headers.get('Location', ''), r.status_code)
r = cliente_cli.post('/copilot', data={'pregunta': 'facturacion del mes'},
                     follow_redirects=False)
check('A3. cliente no puede preguntar (POST)', r.status_code == 302,
      r.status_code)

admin_cli = app.test_client()
admin_cli.post('/login', data={'email': 'admin@asplot.com',
                               'password': 'admin123'})
r = admin_cli.get('/copilot')
html = r.get_data(as_text=True)
check('A4. admin GET /copilot 200', r.status_code == 200, r.status_code)
check('A5. pagina muestra la caja de pregunta',
      'name="pregunta"' in html and 'Copilot administrativo' in html)
check('A6. los 8 chips estan presentes',
      html.count('copilot-chip-form') >= 8, html.count('copilot-chip-form'))
check('A7. aviso de modo plantillas sin API',
      'Modo plantillas' in html)

r = admin_cli.get('/dashboard')
html_dash = r.get_data(as_text=True)
check('A8. dashboard con accion rapida del copilot',
      'Preguntar al copilot' in html_dash)
r = cliente_cli.get('/dashboard')
check('A9. cliente no ve el copilot en su dashboard',
      'Preguntar al copilot' not in r.get_data(as_text=True))

# ---------------------------------------------------------------------------
# 4. Las 8 plantillas responden sin API (POST real con datos sembrados)
# ---------------------------------------------------------------------------
respuestas_plantilla = {}
for plantilla in copilot.PLANTILLAS:
    r = admin_cli.post('/copilot', data={'pregunta': plantilla['ejemplo']})
    html = r.get_data(as_text=True)
    respuestas_plantilla[plantilla['id']] = html
    check('P1. %s responde 200 con tabla' % plantilla['id'],
          r.status_code == 200 and 'copilot-tabla' in html,
          r.status_code)

check('P2. facturacion_mes muestra totales',
      'Cantidad Facturas' in respuestas_plantilla['facturacion_mes']
      and 'Total Facturado' in respuestas_plantilla['facturacion_mes'])
check('P3. top_clientes incluye al cliente sembrado',
      'Siete' in respuestas_plantilla['top_clientes'])
check('P4. proyectos_estado muestra estados',
      'solicitado' in respuestas_plantilla['proyectos_estado']
      and 'ejecutado' in respuestas_plantilla['proyectos_estado'])
check('P5. margen_proyecto con margen calculado',
      'Margen' in respuestas_plantilla['margen_proyecto']
      and 'Costo Insumos' in respuestas_plantilla['margen_proyecto'])
check('P6. consumo_insumos del mes',
      'Rollo prueba A1' in respuestas_plantilla['consumo_insumos'])
check('P7. solicitudes_pendientes lista la pendiente',
      'Solicitud pendiente prueba'
      in respuestas_plantilla['solicitudes_pendientes'])
check('P8. inventario_riesgo lista el material bajo minimo',
      'Rollo prueba A1' in respuestas_plantilla['inventario_riesgo'])
check('P9. planos_tipo agrupa por tipo',
      'Arquitectonico prueba' in respuestas_plantilla['planos_tipo'])
check('P10. badge de fuente Plantilla visible',
      'Plantilla' in respuestas_plantilla['facturacion_mes'])
check('P11. SQL ejecutado visible en <details>',
      'copilot-sql' in respuestas_plantilla['facturacion_mes']
      and 'SELECT' in respuestas_plantilla['facturacion_mes'])

# Pregunta libre reformulada (no es el texto exacto del chip)
r = admin_cli.post('/copilot', data={'pregunta': 'cuanto hemos cobrado este mes'})
html = r.get_data(as_text=True)
check('P12. pregunta reformulada resuelve facturacion_mes',
      'Total Facturado' in html and 'copilot-tabla' in html)

# Pregunta sin coincidencia
r = admin_cli.post('/copilot', data={'pregunta': 'hola mundo xylophone'})
html = r.get_data(as_text=True)
check('P13. sin coincidencia: mensaje con sugerencias, sin tabla',
      'No reconozco' in html and 'copilot-tabla' not in html)
check('P14. sin coincidencia: sugiere las preguntas frecuentes',
      'copilot-chip-inerte' in html)

# Pregunta vacia
r = admin_cli.post('/copilot', data={'pregunta': '   '})
html = r.get_data(as_text=True)
check('P15. pregunta vacia: aviso sin tabla',
      'Escribe una pregunta' in html and 'copilot-tabla' not in html)

# ---------------------------------------------------------------------------
# 5. LLM simulado (monkeypatch sobre copilot.llamar_llm)
# ---------------------------------------------------------------------------
llm_original = copilot.llamar_llm


def restaurar_llm():
    copilot.llamar_llm = llm_original
    app.config['COPILOT_API_KEY'] = None


# 5a. respuesta valida de la IA
app.config['COPILOT_API_KEY'] = 'clave-de-prueba'
copilot.llamar_llm = lambda pregunta, config: {
    'interpretacion': 'Cuenta las facturas registradas',
    'sql': 'SELECT COUNT(*) AS total_facturas FROM facturas',
}
try:
    r = admin_cli.post('/copilot', data={'pregunta': 'cuantas facturas hay'})
    html = r.get_data(as_text=True)
    check('L1. IA valida: fuente IA y respuesta ejecutada',
          'Respondido por IA' in html and 'Cuenta las facturas'
          in html and 'copilot-tabla' in html, r.status_code)
    check('L2. IA valida: SQL de la IA visible',
          'total_facturas' in html)

    # 5b. la IA propone SQL prohibido -> fallback con aviso
    copilot.llamar_llm = lambda pregunta, config: {
        'interpretacion': 'borrar todo',
        'sql': 'DROP TABLE facturas',
    }
    r = admin_cli.post('/copilot', data={'pregunta': 'facturacion del mes'},
                       follow_redirects=True)
    html = r.get_data(as_text=True)
    check('L3. SQL prohibido: cae a plantilla sin 500',
          r.status_code == 200 and 'Plantilla' in html
          and 'copilot-tabla' in html, r.status_code)
    check('L4. SQL prohibido: aviso del rechazo visible',
          'rechazada' in html)

    # 5c. la IA propone una tabla fuera de catalogo -> fallback
    copilot.llamar_llm = lambda pregunta, config: {
        'interpretacion': 'ver usuarios',
        'sql': 'SELECT * FROM usuarios',
    }
    r = admin_cli.post('/copilot', data={'pregunta': 'listado de personal'})
    html = r.get_data(as_text=True)
    check('L5. tabla usuarios rechazada: sin resultados ni 500',
          r.status_code == 200 and 'copilot-tabla' not in html
          and 'No reconozco' in html, r.status_code)

    # 5d. error de red simulado -> fallback sin 500
    def llm_roto(pregunta, config):
        raise copilot.CopilotError('fallo de red simulado')
    copilot.llamar_llm = llm_roto
    r = admin_cli.post('/copilot', data={'pregunta': 'top clientes'})
    html = r.get_data(as_text=True)
    check('L6. error de red: 200 con fallback a plantilla',
          r.status_code == 200 and 'Plantilla' in html
          and 'no pudo responder' in html, r.status_code)

    # 5e. JSON invalido del modelo -> CopilotError -> fallback
    def llm_json_roto(pregunta, config):
        raise copilot.CopilotError('Respuesta del modelo sin JSON valido.')
    copilot.llamar_llm = llm_json_roto
    r = admin_cli.post('/copilot', data={'pregunta': 'planos por tipo'})
    check('L7. JSON invalido: 200 con fallback',
          r.status_code == 200
          and 'Plantilla' in r.get_data(as_text=True), r.status_code)
finally:
    restaurar_llm()

# Sin API key no se llama al LLM (prueba directa del orquestador)
llamadas = []


def llm_trampa(pregunta, config):
    llamadas.append(pregunta)
    return {'interpretacion': 'x', 'sql': 'SELECT 1'}
copilot.llamar_llm = llm_trampa
try:
    resultado = copilot.responder(
        'facturacion del mes', lambda sql, params: ([], []),
        app.config)
    check('L8. sin API key no se consulta al LLM',
          not llamadas and resultado['fuente'] == 'plantilla')
finally:
    restaurar_llm()

# ---------------------------------------------------------------------------
# 6. Log de auditoria
# ---------------------------------------------------------------------------
registros = []


class Capturador(logging.Handler):
    def emit(self, record):
        registros.append(record.getMessage())


capturador = Capturador()
app.logger.addHandler(capturador)
try:
    admin_cli.post('/copilot', data={'pregunta': 'inventario en riesgo'})
finally:
    app.logger.removeHandler(capturador)

lineas_copilot = [m for m in registros if m.startswith('COPILOT')]
check('G1. la consulta queda en el log de auditoria',
      any('usuario=admin' in m and 'fuente=plantilla' in m
          for m in lineas_copilot), lineas_copilot[-1:])
check('G2. el log registra la pregunta y el SQL',
      any('inventario en riesgo' in m and 'SELECT' in m
          for m in lineas_copilot))

# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
print()
if FALLOS:
    print('RESULTADO: %d FALLOS' % len(FALLOS))
    for fallo in FALLOS:
        print(' -', fallo)
    sys.exit(1)
print('RESULTADO: TODAS LAS PRUEBAS EN VERDE')
