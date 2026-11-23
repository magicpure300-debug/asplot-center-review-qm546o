# -*- coding: utf-8 -*-
"""
Ensayo de la demo de ASPLOT CENTER: recorre el guion, mide cada paso y
comprueba que el contenido esperado aparezca.

Uso:
    set ASPLOT_ADMIN_PASSWORD=...
    python scripts/ensayo_demo.py [base_url]

Por defecto usa http://127.0.0.1:5055 (demo local). Para el G60:
    python scripts/ensayo_demo.py http://192.168.0.101:8000/asplot

Requiere Edge y websocket-client. Sale con codigo 1 si algun paso falla.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import websocket

BASE = (sys.argv[1] if len(sys.argv) > 1
        else 'http://127.0.0.1:5055').rstrip('/')
ADMIN_EMAIL = os.environ.get('ASPLOT_ADMIN_EMAIL', 'admin@asplot.com')
ADMIN_PASSWORD = os.environ.get('ASPLOT_ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    sys.exit('Define ASPLOT_ADMIN_PASSWORD antes del ensayo.')

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PUERTO = 9226
PERFIL = os.path.join(os.environ['TEMP'], 'edge_asplot_ensayo')
if os.path.exists(PERFIL):
    shutil.rmtree(PERFIL, ignore_errors=True)
os.makedirs(PERFIL, exist_ok=True)

proceso = subprocess.Popen([
    EDGE, '--headless=new', '--disable-gpu', '--no-first-run',
    '--hide-scrollbars', '--window-size=1440,900',
    '--remote-debugging-port=%d' % PUERTO,
    '--user-data-dir=%s' % PERFIL, 'about:blank',
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def esperar_debugger(intentos=40):
    for _ in range(intentos):
        try:
            with urllib.request.urlopen(
                    'http://127.0.0.1:%d/json/version' % PUERTO, timeout=1) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            time.sleep(0.5)
    raise RuntimeError('Edge no expuso el depurador')


esperar_debugger()
with urllib.request.urlopen('http://127.0.0.1:%d/json' % PUERTO) as r:
    objetivos = json.loads(r.read().decode('utf-8'))
pagina = next(o for o in objetivos if o.get('type') == 'page')
ws = websocket.create_connection(pagina['webSocketDebuggerUrl'], timeout=40)
_contador = [0]


def cmd(metodo, params=None):
    _contador[0] += 1
    ident = _contador[0]
    ws.send(json.dumps({'id': ident, 'method': metodo,
                        'params': params or {}}))
    while True:
        mensaje = json.loads(ws.recv())
        if mensaje.get('id') == ident:
            if 'error' in mensaje:
                raise RuntimeError('%s: %s' % (metodo, mensaje['error']))
            return mensaje.get('result', {})


def js(expresion):
    resultado = cmd('Runtime.evaluate', {
        'expression': expresion, 'returnByValue': True,
        'awaitPromise': True,
    })
    return resultado.get('result', {}).get('value')


def esperar(condicion, segundos=15.0):
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            if js(condicion):
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def navegar(ruta):
    cmd('Page.navigate', {'url': BASE + ruta})
    esperar('document.readyState === "complete"', 30)


def contiene(texto):
    return bool(js('document.body.innerText.indexOf(%s) >= 0'
                   % json.dumps(texto)))


RESULTADOS = []
fallos = 0


def medir(nombre, ruta, esperado=None, accion=None, espera=None):
    inicio = time.perf_counter()
    try:
        navegar(ruta)
        if accion:
            accion()
        if espera:
            esperar(espera, 25)
        duracion = time.perf_counter() - inicio
        ok = True if esperado is None else contiene(esperado)
        RESULTADOS.append((nombre, duracion, ok, '' if ok else
                           'no se encontro: %s' % esperado))
    except Exception as error:
        RESULTADOS.append((nombre, time.perf_counter() - inicio, False,
                           str(error)))


try:
    cmd('Page.enable')
    cmd('Runtime.enable')
    cmd('Emulation.setDeviceMetricsOverride', {
        'width': 1440, 'height': 900, 'deviceScaleFactor': 1,
        'mobile': False,
    })

    medir('Portada publica', '/', 'ASPLOT CENTER')
    medir('Solicitud publica', '/solicitud', 'Solicitar cotización')
    medir('Login', '/login', 'Iniciar')

    inicio = time.perf_counter()
    js("""(() => {
        const email = document.querySelector('input[name=email]');
        const clave = document.querySelector('input[name=password]');
        email.value = %s;
        clave.value = %s;
        clave.closest('form').submit();
        return true;
    })()""" % (json.dumps(ADMIN_EMAIL), json.dumps(ADMIN_PASSWORD)))
    esperar('location.pathname.indexOf("/dashboard") >= 0', 20)
    duracion = time.perf_counter() - inicio
    RESULTADOS.append(('Entrar como admin', duracion,
                       contiene('Panel de control'), ''))

    medir('Dashboard', '/dashboard', 'Panel de control')
    medir('Bandeja de solicitudes', '/solicitudes', 'Solicitudes')
    medir('Listado de clientes', '/clientes', 'Clientes')

    # Ficha 360: primer cliente del listado
    enlace = js("""(() => {
        const enlaces = Array.from(document.querySelectorAll('a[href]'));
        const detalle = enlaces.find(a => /\\/clientes\\/\\d+$/.test(a.getAttribute('href')));
        return detalle ? detalle.getAttribute('href') : null;
    })()""")
    if enlace:
        medir('Ficha del cliente', enlace.replace(BASE, ''), 'Cliente')
    else:
        RESULTADOS.append(('Ficha del cliente', 0.0, False,
                           'no hay enlaces de detalle'))

    # Cotizacion automatica: proyecto de demostracion con PDF A1
    inicio = time.perf_counter()
    navegar('/proyectos/2/aprobar')
    js("document.querySelector('#btn-calcular').click(); true")
    completo = esperar(
        'document.querySelector("#calc-total") && '
        'document.querySelector("#calc-total").innerText.indexOf("$") >= 0', 30)
    RESULTADOS.append(('Cotizacion automatica', time.perf_counter() - inicio,
                       completo, '' if completo else 'sin total sugerido'))

    medir('Inventario predictivo', '/inventario', 'reabastecimiento')
    medir('Calidad del plano', '/planos/detalle/1', 'Calidad del archivo')

    # Validacion de telefono en vivo (sin guardar nada)
    inicio = time.perf_counter()
    navegar('/registro')
    js("""(() => {
        const campo = document.querySelector('#telefono');
        campo.value = '04171917498';
        campo.dispatchEvent(new Event('input', {bubbles: true}));
        return true;
    })()""")
    aviso = esperar("""(() => {
        const ayuda = document.querySelector('[data-telefono-ayuda]');
        return ayuda && ayuda.textContent.indexOf('0417') >= 0 &&
            ayuda.textContent.indexOf('no válido') >= 0;
    })()""", 10)
    RESULTADOS.append(('Validacion de telefono', time.perf_counter() - inicio,
                       aviso, '' if aviso else 'sin aviso de rechazo'))

    medir('Reportes', '/reportes', 'Reporte')

    # Copilot: consulta real
    inicio = time.perf_counter()
    navegar('/copilot')
    js("""(() => {
        const caja = document.querySelector('#pregunta');
        caja.value = 'Cuanto se ha facturado este mes';
        caja.closest('form').submit();
        return true;
    })()""")
    tabla = esperar('document.querySelector("table.copilot-tabla") !== null', 25)
    RESULTADOS.append(('Copilot (consulta)', time.perf_counter() - inicio,
                       tabla, '' if tabla else 'sin tabla de resultados'))

    print()
    print('%-26s %9s  %s' % ('Paso', 'Tiempo', 'Estado'))
    print('-' * 52)
    fallos = 0
    for nombre, duracion, ok, detalle in RESULTADOS:
        print('%-26s %8.2fs  %s %s' % (
            nombre, duracion, 'OK' if ok else 'FALLO',
            detalle if detalle else ''))
        if not ok:
            fallos += 1
    print('-' * 52)
    print('Pasos: %d  Fallos: %d' % (len(RESULTADOS), fallos))
finally:
    try:
        ws.close()
    except Exception:
        pass
    proceso.terminate()

sys.exit(1 if fallos else 0)
