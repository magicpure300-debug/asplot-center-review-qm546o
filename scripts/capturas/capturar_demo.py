# -*- coding: utf-8 -*-
"""
Capturas de la demo de ASPLOT CENTER con Edge headless + CDP.

Requiere: websocket-client (pip) y Microsoft Edge.
Uso:  python capturar_demo.py <base_url> <carpeta_salida>
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

BASE = (sys.argv[1] if len(sys.argv) > 1
        else 'http://192.168.0.101:8000/asplot').rstrip('/')
SALIDA = (sys.argv[2] if len(sys.argv) > 2
          else os.path.join(os.environ['TEMP'], 'capturas_asplot'))
ADMIN_EMAIL = os.environ.get('ASPLOT_ADMIN_EMAIL', 'admin@asplot.com')
ADMIN_PASSWORD = os.environ.get('ASPLOT_ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    sys.exit('Define ASPLOT_ADMIN_PASSWORD antes de ejecutar las capturas.')
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PUERTO = 9223
PERFIL = os.path.join(os.environ['TEMP'], 'edge_asplot_capturas')

os.makedirs(SALIDA, exist_ok=True)
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


version = esperar_debugger()
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
        time.sleep(0.35)
    return False


def navegar(ruta, espera=0.6):
    cmd('Page.navigate', {'url': BASE + ruta})
    esperar('document.readyState === "complete"', 25)
    time.sleep(espera)


def capturar(nombre):
    datos = cmd('Page.captureScreenshot', {'format': 'png'})
    ruta = os.path.join(SALIDA, nombre)
    with open(ruta, 'wb') as archivo:
        archivo.write(base64.b64decode(datos['data']))
    print('captura:', ruta)


try:
    cmd('Page.enable')
    cmd('Runtime.enable')
    cmd('Emulation.setDeviceMetricsOverride', {
        'width': 1440, 'height': 900, 'deviceScaleFactor': 1,
        'mobile': False,
    })

    # 1. Landing
    navegar('/')
    capturar('00-landing.png')

    # 2. Login y dashboard
    navegar('/login')
    js("""(() => {
        const email = document.querySelector('input[name=email]');
        const clave = document.querySelector('input[name=password]');
        email.value = %s;
        clave.value = %s;
        clave.closest('form').submit();
        return true;
    })()""" % (json.dumps(ADMIN_EMAIL), json.dumps(ADMIN_PASSWORD)))
    esperar('location.pathname.indexOf("/dashboard") >= 0', 20)
    time.sleep(1.2)
    capturar('01-dashboard.png')

    # 3. Copilot con una consulta real
    navegar('/copilot')
    js("""(() => {
        const caja = document.querySelector('#pregunta');
        caja.value = '¿Cuánto se ha facturado este mes?';
        caja.closest('form').submit();
        return true;
    })()""")
    esperar('document.querySelector("table.copilot-tabla") !== null', 20)
    time.sleep(0.6)
    capturar('02-copilot.png')

    # 4. Inventario predictivo
    navegar('/inventario', espera=1.0)
    capturar('03-inventario.png')

    # 5. Cotizacion automatica
    navegar('/proyectos/2/aprobar')
    js("document.querySelector('#btn-calcular').click(); true")
    esperar('document.querySelector("#calc-desglose") && !document.querySelector("#calc-desglose").hidden', 25)
    time.sleep(0.6)
    js("document.querySelector('#calc-desglose').scrollIntoView({block: 'center'}); true")
    time.sleep(0.4)
    capturar('04-cotizacion.png')

    # 6. Calidad de planos
    navegar('/planos/detalle/1', espera=0.9)
    capturar('05-calidad-plano.png')

    # 7. Validacion de telefono en el registro
    navegar('/registro')
    js("""(() => {
        const campo = document.querySelector('#telefono');
        campo.value = '04171917498';
        campo.dispatchEvent(new Event('input', {bubbles: true}));
        campo.scrollIntoView({block: 'center'});
        return true;
    })()""")
    time.sleep(0.6)
    capturar('06-telefono.png')

    print('LISTO')
finally:
    try:
        ws.close()
    except Exception:
        pass
    proceso.terminate()
