# -*- coding: utf-8 -*-
"""Smoke del rediseno: clases nuevas y rutas por rol."""
import os
import shutil
import sys
import tempfile

ORIGEN = os.environ.get(
    'ASPLOT_ORIGEN', r'C:\Users\L\Desktop\Programa Asplot\Programa Asplot')
DESTINO = os.path.join(tempfile.gettempdir(), 'asplot_diseno_test')
IGNORAR = shutil.ignore_patterns('venv', '.venv', '__pycache__', 'instance',
                                 '*.pyc', 'migracion', '.git', 'specs')

if os.path.exists(DESTINO):
    shutil.rmtree(DESTINO)
shutil.copytree(ORIGEN, DESTINO, ignore=IGNORAR)
os.makedirs(os.path.join(DESTINO, 'instance'), exist_ok=True)
os.chdir(DESTINO)
sys.path.insert(0, DESTINO)

from app import create_app
from models import db, Usuario, Cliente, Proyecto

app = create_app()
app.config['TESTING'] = True
FALLOS = []


def check(nombre, cond, detalle=''):
    if cond:
        print('OK   ', nombre)
    else:
        FALLOS.append(nombre)
        print('FALLO', nombre, detalle)


with app.app_context():
    admin = Usuario.query.filter_by(email='admin@asplot.com').first()
    admin.set_password('admin123')
    cli = Usuario(nombre_usuario='cli7', email='cli7@test.com', rol='cliente',
                  nombre_completo='Cliente Siete', activo=True)
    cli.set_password('cliente123')
    db.session.add(cli)
    db.session.flush()
    cliente = Cliente(nombre='Cliente', apellido='Siete', email='cli7@test.com',
                      telefono='04140000007', direccion='Maturin',
                      id_usuario=cli.id_usuario)
    db.session.add(cliente)
    db.session.flush()
    db.session.add(Proyecto(id_cliente=cliente.id_cliente,
                            nombre_proyecto='Proyecto diseno',
                            descripcion='Prueba de rediseno',
                            tipo_servicio='plano', estado='cotizado',
                            presupuesto=120))
    db.session.commit()

anon = app.test_client()
r = anon.get('/')
html = r.get_data(as_text=True)
check('landing 200 con hero', r.status_code == 200 and 'class="hero"' in html)
check('landing usa Space Grotesk', 'Space+Grotesk' in html)

r = anon.get('/login')
html = r.get_data(as_text=True)
check('login 200 con tarjeta', r.status_code == 200 and 'login-card' in html)
check('login usa Space Grotesk', 'Space+Grotesk' in html)

r = anon.get('/solicitud')
check('solicitud publica 200', r.status_code == 200)

admin_cli = app.test_client()
admin_cli.post('/login', data={'email': 'admin@asplot.com', 'password': 'admin123'})
r = admin_cli.get('/dashboard')
html = r.get_data(as_text=True)
check('dashboard admin 200', r.status_code == 200)
check('dashboard admin: acciones rapidas', 'acciones-rapidas' in html)
check('dashboard admin: tarjetas de alerta', 'alerta-card' in html and 'alerta-numero' in html)
check('layout: breadcrumb', 'breadcrumb' in html)
check('layout: grupos del sidebar', 'sidebar-grupo' in html and 'Comercial' in html
      and 'Produccion' in html.replace('ó', 'o') or 'Producción' in html)
check('layout: badge de solicitudes', 'nav-badge' in html)

r = admin_cli.get('/inventario')
html = r.get_data(as_text=True)
check('inventario 200 con ancla de prediccion',
      r.status_code == 200 and 'id="prediccion"' in html)

for ruta in ('/clientes', '/proyectos', '/planos', '/facturas', '/solicitudes', '/usuarios'):
    r = admin_cli.get(ruta)
    check('admin %s 200' % ruta, r.status_code == 200, r.status_code)

cli_cli = app.test_client()
cli_cli.post('/login', data={'email': 'cli7@test.com', 'password': 'cliente123'})
r = cli_cli.get('/dashboard')
html = r.get_data(as_text=True)
check('dashboard cliente 200', r.status_code == 200)
check('dashboard cliente: linea de estado', 'timeline-estado' in html
      and 'timeline-paso' in html)
check('dashboard cliente: etapa actual', 'timeline-paso actual' in html
      or 'timeline-paso actual' in html)
check('cliente no ve grupo Comercial', 'Comercial' not in html)
check('cliente ve Mi cuenta', 'Mi cuenta' in html)

r = cli_cli.get('/mis-planos')
check('cliente /mis-planos 200', r.status_code == 200)

print()
if FALLOS:
    print('RESULTADO: %d FALLOS' % len(FALLOS))
    for fallo in FALLOS:
        print(' -', fallo)
    sys.exit(1)
print('RESULTADO: SMOKE DE DISENO EN VERDE')
