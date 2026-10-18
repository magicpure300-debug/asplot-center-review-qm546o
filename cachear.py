# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 3 (PB-06)
 Sistema de caché en memoria con TTL (Time-To-Live)
=============================================================================
 Módulo ligero sin dependencias externas, pensado para el despliegue actual
 de la aplicación (instancia Flask única, servidor de desarrollo o gunicorn
 con workers synchronizados).

 Características:
   - Caché en memoria del proceso (dict + bloqueo: seguro ante hilos).
   - TTL configurable por clave o por defecto.
   - Invalidación exacta por claves o por prefijo (ej: toda la caché del
     dashboard cuando se crea un cliente).
   - Decorador `cachear_ruta` optimizado para vistas Flask: incluye el
     método HTTP y la query string en la clave, y NO cachea respuestas
     con error o redirecciones.

 Limitación conocida (documentada en docs/SPRINT_3.md): cada proceso
 gunicorn mantiene su propia caché. Para múltiples instancias se recomienda
 migrar a Redis cambiando solo el backend de este módulo.

 Uso:
     from cachear import cache, cachear_ruta

     @app.route('/dashboard')
     @cachear_ruta(ttl=60)
     def dashboard(): ...

     cache.invalidar_prefijo('ruta:/dashboard')   # al escribir datos
=============================================================================
"""

import threading
import time
from functools import wraps

from flask import request


class CacheMemoria:
    """Caché en memoria thread-safe con TTL y invalidación por prefijo."""

    def __init__(self, ttl_defecto=60):
        self._datos = {}
        self._bloqueo = threading.RLock()
        self._ttl_defecto = ttl_defecto
        self.aciertos = 0
        self.fallos = 0

    # ------------------------------------------------------------------ #
    # Operaciones básicas
    # ------------------------------------------------------------------ #
    def obtener(self, clave):
        """Devuelve el valor cacheado o None si expiró/no existe."""
        with self._bloqueo:
            entrada = self._datos.get(clave)
            if entrada is None:
                self.fallos += 1
                return None
            valor, expira = entrada
            if expira and time.time() > expira:
                del self._datos[clave]
                self.fallos += 1
                return None
            self.aciertos += 1
            return valor

    def poner(self, clave, valor, ttl=None):
        """Almacena un valor. ttl=None usa el TTL por defecto; ttl=0 = eterno."""
        ttl = self._ttl_defecto if ttl is None else ttl
        expira = time.time() + ttl if ttl else None
        with self._bloqueo:
            self._datos[clave] = (valor, expira)

    def invalidar(self, clave):
        with self._bloqueo:
            self._datos.pop(clave, None)

    def invalidar_prefijo(self, prefijo):
        """Invalida todas las claves que empiecen por el prefijo dado."""
        with self._bloqueo:
            claves = [k for k in self._datos if k.startswith(prefijo)]
            for k in claves:
                del self._datos[k]
            return len(claves)

    def invalidar_contiene(self, texto):
        """
        Invalida todas las claves que contengan el texto dado en cualquier
        posición. Útil para las claves de vista (ruta:usuario:...) donde el
        identificador de la vista va después del usuario.
        """
        with self._bloqueo:
            claves = [k for k in self._datos if texto in k]
            for k in claves:
                del self._datos[k]
            return len(claves)

    def limpiar(self):
        with self._bloqueo:
            self._datos.clear()

    def estadisticas(self):
        with self._bloqueo:
            total = self.aciertos + self.fallos
            return {
                'entradas': len(self._datos),
                'aciertos': self.aciertos,
                'fallos': self.fallos,
                'efectividad': (self.aciertos / total * 100) if total else 0.0,
            }


# Instancia única del proceso
cache = CacheMemoria(ttl_defecto=60)


# =============================================================================
# Decorador para vistas Flask
# =============================================================================
def cachear_ruta(ttl=60, solo_get=True):
    """
    Cachea la respuesta de una vista Flask en memoria.

    La clave incluye: método HTTP + endpoint + query string, por lo que dos
    filtros diferentes generan entradas distintas. Solo se cachean respuestas
    200 con cuerpo (no redirecciones, flashes ni errores).

    Args:
        ttl: segundos de vida de la entrada.
        solo_get: si es True (por defecto) ignora peticiones que no sean GET.
    """

    def decorador(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            if solo_get and request.method != 'GET':
                return func(*args, **kwargs)

            # La clave incluye la identidad del usuario: las vistas con
            # contenido por rol (dashboard admin/cliente) NO deben compartir
            # entrada, o se filtrarían datos entre sesiones.
            from flask_login import current_user
            usuario_id = current_user.get_id() if current_user.is_authenticated else 'anon'

            clave = f'ruta:{usuario_id}:{request.method}:{request.full_path}{func.__name__}'
            valor = cache.obtener(clave)
            if valor is not None:
                return valor

            respuesta = func(*args, **kwargs)
            # Solo cacheamos respuestas exitosas con cuerpo (status 200)
            if isinstance(respuesta, tuple):
                cuerpo, status = respuesta[0], respuesta[1]
            else:
                cuerpo, status = respuesta, 200

            if status == 200:
                cache.poner(clave, respuesta, ttl=ttl)
            return respuesta

        return envoltura

    return decorador
