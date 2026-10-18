# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 2 (PB-04)
 Prueba de rendimiento: tiempo y número de consultas por ruta
=============================================================================
 Mide las rutas más consultadas del sistema con el test client de Flask,
 contando:
   - Tiempo total de la petición (ms)
   - Número de sentencias SQL ejecutadas (detecta patrones N+1)
   - Tiempo acumulado dentro del motor de BD (ms)

 Sirve como evidencia objetiva de la Sprint Review del Sprint 2:
   - Sin índices eager loading / consolidación: línea base
   - Con ellos: comparativa (ejecutar antes y después de aplicar los cambios)

 Uso:
   python perf_test.py                  # rutas del panel admin (loguea admin)
   python perf_test.py --iteraciones 5  # promediar 5 ejecuciones por ruta
=============================================================================
"""

import argparse
import os
import statistics
import sys
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app                     # noqa: E402
from models import db                          # noqa: E402
from sqlalchemy import event                   # noqa: E402
from sqlalchemy.engine import Engine           # noqa: E402

# Contadores por petición
estado = {'queries': 0, 'tiempo_bd': 0.0}


@event.listens_for(Engine, 'before_cursor_execute')
def _antes(conn, cursor, statement, parameters, context, executemany):
    estado['queries'] += 1
    estado['_inicio'] = time.perf_counter()


@event.listens_for(Engine, 'after_cursor_execute')
def _despues(conn, cursor, statement, parameters, context, executemany):
    estado['tiempo_bd'] += (time.perf_counter() - estado.get('_inicio', time.perf_counter())) * 1000


RUTAS_ADMIN = [
    ('GET', '/dashboard'),
    ('GET', '/clientes'),
    ('GET', '/proyectos?estado=todas'),
    ('GET', '/planos'),
    ('GET', '/inventario'),
    ('GET', '/facturas'),
    ('GET', '/planos/buscar?nombre=a'),
    ('GET', '/reportes'),
]

RUTAS_PUBLICAS = [
    ('GET', '/'),
    ('GET', '/login'),
]


def crear_cliente_prueba(app):
    """Cliente de prueba autenticado como administrador."""
    from werkzeug.test import Client
    client = app.test_client()

    with app.app_context():
        from models import Usuario
        usuario = Usuario.query.filter_by(email='admin@asplot.com').first()
        if not usuario:
            print('[ERROR] No existe el usuario admin@asplot.com. Ejecute primero init_db.py')
            sys.exit(1)

    # Login real contra la ruta /login (valida contraseña)
    client.post('/login', data={
        'email': 'admin@asplot.com',
        'password': 'admin123',
    }, follow_redirects=False)
    return client


def medir_ruta(client, metodo, ruta, iteraciones):
    tiempos, consultas, tiempo_bd = [], [], []
    for _ in range(iteraciones):
        estado['queries'] = 0
        estado['tiempo_bd'] = 0.0
        t0 = time.perf_counter()
        respuesta = client.open(ruta, method=metodo)
        total_ms = (time.perf_counter() - t0) * 1000
        if respuesta.status_code >= 500:
            return None, None, None, respuesta.status_code
        tiempos.append(total_ms)
        consultas.append(estado['queries'])
        tiempo_bd.append(estado['tiempo_bd'])
    return (statistics.mean(tiempos), statistics.mean(consultas),
            statistics.mean(tiempo_bd), None)


def main():
    parser = argparse.ArgumentParser(description='Prueba de rendimiento (Sprint 2 - PB-04)')
    parser.add_argument('--iteraciones', type=int, default=3,
                        help='Ejecuciones por ruta (para promediar)')
    parser.add_argument('--publico', action='store_true',
                        help='Medir también rutas públicas')
    args = parser.parse_args()

    app = create_app()
    app.config['LOGIN_DISABLED'] = False
    client = crear_cliente_prueba(app)

    rutas = RUTAS_ADMIN + (RUTAS_PUBLICAS if args.publico else [])

    print('=' * 78)
    print(' ASPLOT CENTER - Prueba de rendimiento (Sprint 2 / PB-04)')
    print(f' Iteraciones por ruta: {args.iteraciones}')
    print('=' * 78)
    print(f'{"RUTA":<38} {"ms":>8} {"SQL":>6} {"BD ms":>8}  Estado')
    print('-' * 78)

    problemas = []
    for metodo, ruta in rutas:
        ms, nsql, bd_ms, codigo_error = medir_ruta(client, metodo, ruta, args.iteraciones)
        if codigo_error:
            print(f'{ruta:<38} {"-":>8} {"-":>6} {"-":>8}  HTTP {codigo_error}')
            problemas.append((ruta, codigo_error))
            continue
        print(f'{ruta:<38} {ms:>8.1f} {nsql:>6.0f} {bd_ms:>8.2f}  OK')

    print('-' * 78)
    if problemas:
        print('Rutas con error:')
        for ruta, codigo in problemas:
            print(f'  ! HTTP {codigo}: {ruta}')
        sys.exit(1)
    print('Todas las rutas respondieron correctamente.')


if __name__ == '__main__':
    main()
