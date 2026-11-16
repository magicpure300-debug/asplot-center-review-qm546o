# -*- coding: utf-8 -*-
"""
Pruebas Sprint 8: validacion de telefonos de Venezuela.

Copia limpia del proyecto con SQLite propio (patron de sprints anteriores).
Cubre el modulo, las 7 rutas de escritura, las plantillas y la sincronia
del catalogo entre Python y el JavaScript del navegador.
"""
import os
import re
import shutil
import sys
import tempfile
import unicodedata

ORIGEN = os.environ.get(
    'ASPLOT_ORIGEN', r'C:\Users\L\Desktop\Programa Asplot\Programa Asplot')
DESTINO = os.path.join(tempfile.gettempdir(), 'asplot_sprint8_test')

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
from models import db, Usuario, Cliente, Proyecto            # noqa: E402
import validacion_telefono as tel                            # noqa: E402

app = create_app()
app.config['TESTING'] = True

FALLOS = []


def check(nombre, cond, detalle=''):
    if cond:
        print('OK   ', nombre)
    else:
        FALLOS.append(nombre)
        print('FALLO', nombre, detalle)


def sin_acentos(texto):
    normal = unicodedata.normalize('NFD', texto or '')
    return ''.join(c for c in normal if unicodedata.category(c) != 'Mn').lower()


def visible(html):
    return sin_acentos(html)


with app.app_context():
    admin = Usuario.query.filter_by(email='admin@asplot.com').first()
    admin.set_password('admin123')
    existente = Cliente(nombre='Cliente', apellido='Telefono',
                        email='cliente.tel@test.com', telefono='04141112233',
                        direccion='Maturin')
    db.session.add(existente)
    db.session.commit()

# Contexto permanente para consultar la base fuera de las peticiones.
_ctx = app.app_context()
_ctx.push()
admin = Usuario.query.filter_by(email='admin@asplot.com').first()
existente = Cliente.query.filter_by(email='cliente.tel@test.com').first()

# ---------------------------------------------------------------------------
# 1. Modulo: telefonos validos
# ---------------------------------------------------------------------------
for numero, operadora in [
    ('04121917498', 'Digitel'), ('04221917498', 'Digitel'),
    ('04141917498', 'Movistar'), ('04241917498', 'Movistar'),
    ('04161917498', 'Movilnet'), ('04261917498', 'Movilnet'),
    ('04151917498', 'Tesan'),
]:
    datos = tel.normalizar_telefono(numero)
    check('U. movil valido %s -> %s' % (numero, operadora),
          datos['ok'] and datos['tipo'] == 'movil'
          and datos['operadora'] == operadora, datos['error'])

datos = tel.normalizar_telefono('+58 414-1917498')
check('U. +58 con espacios y guion se normaliza',
      datos['ok'] and datos['valor'] == '04141917498', datos['error'])

datos = tel.normalizar_telefono('0058 291 1234567')
check('U. 0058 fijo -> 02911234567',
      datos['ok'] and datos['valor'] == '02911234567'
      and datos['tipo'] == 'fijo' and datos['estado'] == 'Monagas',
      datos['error'])

datos = tel.normalizar_telefono('4141917498')
check('U. movil sin cero inicial se completa',
      datos['ok'] and datos['valor'] == '04141917498', datos['error'])

datos = tel.normalizar_telefono('(0212) 555-1212')
check('U. fijo 0212 con parentesis y guion',
      datos['ok'] and datos['valor'] == '02125551212'
      and 'Distrito Capital' in datos['estado'], datos['error'])

check('U. formatear movil', tel.formatear_telefono('04141917498')
      == '0414-1917498')
check('U. describir movil', tel.describir_telefono('04141917498')
      == 'Móvil Movistar')
check('U. describir fijo', 'Monagas' in tel.describir_telefono('02911234567'))

# ---------------------------------------------------------------------------
# 2. Modulo: telefonos invalidos
# ---------------------------------------------------------------------------
casos_invalidos = [
    ('0414191749', '10 digitos'),
    ('041419174981', '12 digitos'),
    ('04171917498', 'prefijo eliminado 0417'),
    ('04181917498', 'prefijo eliminado 0418'),
    ('03001917498', 'prefijo inexistente'),
    ('02991234567', 'codigo de area inexistente'),
    ('0414ABC7498', 'letras'),
    ('00000000000', 'todos los digitos iguales'),
    ('   ', 'vacio'),
]
for valor, motivo in casos_invalidos:
    datos = tel.normalizar_telefono(valor)
    check('U. rechaza %s' % motivo, not datos['ok'] and datos['error'],
          datos)

check('U. vacio opcional se acepta',
      tel.validar_telefono('', obligatorio=False) == (True, '', None))
check('U. error de longitud explica el conteo',
      '11' in tel.validar_telefono('0414191749')[2])

# Catalogo sincronizado con el JavaScript
ruta_js = os.path.join(DESTINO, 'static', 'js', 'telefono.js')
with open(ruta_js, 'r', encoding='utf-8') as archivo:
    js = archivo.read()
prefijos_js = set(re.findall(r"'(04\d\d)':", js))
areas_js = set(re.findall(r"'(2\d\d)':", js))
check('U. prefijos del JS coinciden con Python',
      prefijos_js == set(tel.PREFIJOS_MOVIL), (prefijos_js,
                                               set(tel.PREFIJOS_MOVIL)))
check('U. areas del JS coinciden con Python',
      areas_js == set(tel.CODIGOS_AREA), (len(areas_js),
                                          len(tel.CODIGOS_AREA)))

# ---------------------------------------------------------------------------
# 3. Rutas: registro
# ---------------------------------------------------------------------------
publico = app.test_client()
r = publico.post('/registro', data={
    'nombre': 'Malo', 'apellido': 'Telefono', 'email': 'malo.tel@test.com',
    'telefono': '123', 'direccion': 'x', 'password': 'clave123',
    'password_confirm': 'clave123'}, follow_redirects=True)
html = visible(r.get_data(as_text=True))
check('R1. registro con telefono corto no crea usuario',
      Usuario.query.filter_by(email='malo.tel@test.com').first() is None)
check('R2. registro muestra el motivo del rechazo',
      'telefono invalido' in html and '11 digitos' in html)

r = publico.post('/registro', data={
    'nombre': 'Bueno', 'apellido': 'Telefono', 'email': 'bueno.tel@test.com',
    'telefono': '+58 416-1234567', 'direccion': 'x', 'password': 'clave123',
    'password_confirm': 'clave123'}, follow_redirects=True)
usuario = Usuario.query.filter_by(email='bueno.tel@test.com').first()
check('R3. registro valido normaliza y guarda el telefono',
      usuario is not None and usuario.telefono == '04161234567',
      usuario and usuario.telefono)

# ---------------------------------------------------------------------------
# 4. Rutas: clientes (admin)
# ---------------------------------------------------------------------------
admin_cli = app.test_client()
admin_cli.post('/login', data={'email': 'admin@asplot.com',
                               'password': 'admin123'})

r = admin_cli.post('/clientes/crear', data={
    'nombre': 'Cliente', 'apellido': 'Malo', 'email': 'cliente.malo@test.com',
    'telefono': '04171917498', 'direccion': 'x'}, follow_redirects=True)
check('R4. crear cliente con prefijo invalido no guarda',
      Cliente.query.filter_by(email='cliente.malo@test.com').first() is None)
check('R5. crear cliente muestra el error',
      'telefono invalido' in visible(r.get_data(as_text=True)))

r = admin_cli.post('/clientes/crear', data={
    'nombre': 'Cliente', 'apellido': 'Bueno',
    'email': 'cliente.bueno@test.com', 'telefono': '0414-1917498',
    'direccion': 'x'}, follow_redirects=True)
nuevo = Cliente.query.filter_by(email='cliente.bueno@test.com').first()
check('R6. crear cliente valido guarda el canonico',
      nuevo is not None and nuevo.telefono == '04141917498',
      nuevo and nuevo.telefono)

r = admin_cli.post('/clientes/editar/%d' % existente.id_cliente, data={
    'nombre': 'Cliente', 'apellido': 'Telefono',
    'email': 'cliente.tel@test.com', 'telefono': '0414',
    'direccion': 'Maturin'}, follow_redirects=True)
db.session.refresh(existente)
check('R7. editar cliente con telefono corto no cambia',
      existente.telefono == '04141112233', existente.telefono)

r = admin_cli.post('/clientes/editar/%d' % existente.id_cliente, data={
    'nombre': 'Cliente', 'apellido': 'Telefono',
    'email': 'cliente.tel@test.com', 'telefono': '0291-1234567',
    'direccion': 'Maturin'}, follow_redirects=True)
db.session.refresh(existente)
check('R8. editar cliente valido normaliza',
      existente.telefono == '02911234567', existente.telefono)

# ---------------------------------------------------------------------------
# 5. Rutas: solicitud publica
# ---------------------------------------------------------------------------
datos_solicitud = {
    'nombre': 'Solicitante', 'apellido': 'Prueba',
    'email': 'solicitud.tel@test.com', 'telefono': '0416-12',
    'direccion': 'Maturin', 'tipo_servicio': 'plano',
    'nombre_proyecto': 'Proyecto telefono', 'descripcion': 'Prueba',
}
r = publico.post('/solicitud', data=datos_solicitud)
check('R9. solicitud con telefono invalido responde 400',
      r.status_code == 400, r.status_code)
check('R10. solicitud invalida no crea proyecto',
      Proyecto.query.filter_by(nombre_proyecto='Proyecto telefono').first()
      is None)
check('R11. solicitud muestra el error junto al campo',
      '11 digitos' in visible(r.get_data(as_text=True)))

datos_solicitud['telefono'] = '+58 424 1234567'
r = publico.post('/solicitud', data=datos_solicitud)
proyecto = Proyecto.query.filter_by(nombre_proyecto='Proyecto telefono').first()
check('R12. solicitud valida se crea', proyecto is not None,
      r.status_code)
cliente_sol = Cliente.query.filter_by(email='solicitud.tel@test.com').first()
check('R13. solicitud guarda el telefono canonico',
      cliente_sol is not None and cliente_sol.telefono == '04241234567',
      cliente_sol and cliente_sol.telefono)

# ---------------------------------------------------------------------------
# 6. Rutas: usuarios y configuracion
# ---------------------------------------------------------------------------
r = admin_cli.post('/usuarios/crear', data={
    'nombre_usuario': 'usuariomalo', 'email': 'usuariomalo@test.com',
    'rol': 'trabajador', 'nombre_completo': 'Usuario Malo',
    'telefono': '999', 'direccion': 'x', 'password': 'clave123'},
    follow_redirects=True)
check('R14. crear usuario con telefono invalido no guarda',
      Usuario.query.filter_by(email='usuariomalo@test.com').first() is None)

r = admin_cli.post('/usuarios/crear', data={
    'nombre_usuario': 'usuariobueno', 'email': 'usuariobueno@test.com',
    'rol': 'trabajador', 'nombre_completo': 'Usuario Bueno',
    'telefono': '0412-1234567', 'direccion': 'x', 'password': 'clave123'},
    follow_redirects=True)
u = Usuario.query.filter_by(email='usuariobueno@test.com').first()
check('R15. crear usuario valido normaliza',
      u is not None and u.telefono == '04121234567', u and u.telefono)

r = admin_cli.post('/usuarios/crear', data={
    'nombre_usuario': 'usuariosintelefono', 'email': 'sin.tel@test.com',
    'rol': 'trabajador', 'nombre_completo': 'Sin Telefono',
    'telefono': '', 'direccion': 'x', 'password': 'clave123'},
    follow_redirects=True)
u = Usuario.query.filter_by(email='sin.tel@test.com').first()
check('R16. telefono opcional vacio sigue permitido',
      u is not None and u.telefono == '', u and u.telefono)

r = admin_cli.post('/usuarios/editar/%d' % u.id_usuario, data={
    'nombre_usuario': 'usuariosintelefono', 'email': 'sin.tel@test.com',
    'rol': 'trabajador', 'nombre_completo': 'Sin Telefono',
    'telefono': '0417', 'direccion': 'x'}, follow_redirects=True)
db.session.refresh(u)
check('R17. editar usuario con telefono invalido no cambia',
      u.telefono == '', u.telefono)

r = admin_cli.post('/configuracion/actualizar', data={
    'nombre_usuario': 'admin', 'email': 'admin@asplot.com',
    'nombre_completo': 'Administrador', 'telefono': '0414-19',
    'direccion': 'x'}, follow_redirects=True)
db.session.refresh(admin)
check('R18. configuracion rechaza telefono invalido',
      admin.telefono != '0414-19')

admin_cli.post('/configuracion/actualizar', data={
    'nombre_usuario': 'admin', 'email': 'admin@asplot.com',
    'nombre_completo': 'Administrador', 'telefono': '0291-5551212',
    'direccion': 'Maturin'})
db.session.refresh(admin)
check('R19. configuracion guarda el canonico',
      admin.telefono == '02915551212', admin.telefono)

# ---------------------------------------------------------------------------
# 7. Plantillas y estilos
# ---------------------------------------------------------------------------
paginas = {
    'registro': '/registro',
    'crear_cliente': '/clientes/crear',
    'editar_cliente': '/clientes/editar/%d' % existente.id_cliente,
    'solicitud_publica': '/solicitud',
    'crear_usuario': '/usuarios/crear',
    'editar_usuario': '/usuarios/editar/%d' % u.id_usuario,
    'configuracion': '/configuracion',
}
for nombre, ruta in paginas.items():
    html = admin_cli.get(ruta).get_data(as_text=True)
    check('T. %s carga telefono.js' % nombre,
          'js/telefono.js' in html, ruta)
    check('T. %s muestra ayuda de formato' % nombre,
          'data-telefono-ayuda' in html, ruta)

with open(os.path.join(DESTINO, 'static', 'css', 'style.css'),
          'r', encoding='utf-8') as archivo:
    css = archivo.read()
check('T. estilos de ayuda definidos', '.campo-ayuda' in css
      and '.campo-ayuda-error' in css)

# ---------------------------------------------------------------------------
print()
if FALLOS:
    print('RESULTADO: %d FALLOS' % len(FALLOS))
    for fallo in FALLOS:
        print(' -', fallo)
    sys.exit(1)
print('RESULTADO: TODAS LAS PRUEBAS EN VERDE')
