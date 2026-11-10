# -*- coding: utf-8 -*-
"""
ASPLOT CENTER - Configuración de la aplicación
Sprint 1 (PB-01): soporte de MySQL mediante variables de entorno,
manteniendo SQLite como opción de respaldo mientras MySQL no esté
disponible en producción (Patrón Strangler Fig).

Variables de entorno para activar MySQL:
    MYSQL_HOST      (ej: localhost)
    MYSQL_PORT      (ej: 3306)
    MYSQL_USER      (ej: root)
    MYSQL_PASSWORD  (ej: secret)
    MYSQL_DATABASE  (ej: asplot_center)

Si MYSQL_HOST y MYSQL_PASSWORD NO están definidas, la aplicación
continúa operando sobre SQLite (compatibilidad hacia atrás).
"""

import os


def get_database_url():
    """
    Construye la URL de conexión a la base de datos.
    - Si las variables de entorno MySQL están presentes -> MySQL.
    - En caso contrario                      -> SQLite (respaldo).
    """
    host = os.environ.get('MYSQL_HOST')
    password = os.environ.get('MYSQL_PASSWORD')

    # Criterio de conmutación (Strangler Fig): MySQL solo cuando está configurado
    if host and password is not None and os.environ.get('MYSQL_USER'):
        user = os.environ.get('MYSQL_USER', 'root')
        port = os.environ.get('MYSQL_PORT', '3306')
        database = os.environ.get('MYSQL_DATABASE', 'asplot_center')
        return f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4'

    return 'sqlite:///asplot_database.db'


def es_mysql():
    """Indica si la aplicación apunta a MySQL o a SQLite."""
    return get_database_url().startswith('mysql')


class Config:
    """Configuración base para la aplicación Flask"""

    # Configuración de la base de datos (SQLite por defecto, MySQL por env vars)
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY', 'asplot-center-secret-key-2025')

    # Configuración de archivos
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'planos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB máximo por archivo

    # Tipos de archivos permitidos para planos
    ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'jpg', 'jpeg', 'png'}

    # Configuración de sesión
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora

    # =========================================================================
    # Sprint 5 (PB-10) - Cotización automática
    # Tarifa de venta por m² y margen; rendimientos estimados de los insumos
    # (m² que cubre un rollo de papel / un cartucho de tinta). Configurables
    # por entorno para ajustar la demo sin tocar código.
    # =========================================================================
    COTIZACION_TARIFA_M2 = float(os.environ.get('COTIZACION_TARIFA_M2', '8.0'))
    COTIZACION_MARGEN_PCT = float(os.environ.get('COTIZACION_MARGEN_PCT', '30'))
    COTIZACION_RENDIMIENTO_ROLLO_M2 = float(
        os.environ.get('COTIZACION_RENDIMIENTO_ROLLO_M2', '10'))
    COTIZACION_RENDIMIENTO_CARTUCHO_M2 = float(
        os.environ.get('COTIZACION_RENDIMIENTO_CARTUCHO_M2', '20'))

    # =========================================================================
    # Sprint 6 (PB-11 / PB-13) - Inventario predictivo y calidad de planos
    # =========================================================================
    INVENTARIO_VENTANA_DIAS = int(os.environ.get('INVENTARIO_VENTANA_DIAS', '90'))
    INVENTARIO_DIAS_REPOSICION = float(
        os.environ.get('INVENTARIO_DIAS_REPOSICION', '7'))
    INVENTARIO_DIAS_SEGURIDAD = float(
        os.environ.get('INVENTARIO_DIAS_SEGURIDAD', '7'))
    INVENTARIO_DIAS_COMPRA = float(os.environ.get('INVENTARIO_DIAS_COMPRA', '30'))
    INVENTARIO_FACTOR_ACTIVO = float(
        os.environ.get('INVENTARIO_FACTOR_ACTIVO', '0.10'))
    INVENTARIO_TOPE_ACTIVO = float(
        os.environ.get('INVENTARIO_TOPE_ACTIVO', '0.50'))
    INVENTARIO_SILENCIO_DIAS = int(
        os.environ.get('INVENTARIO_SILENCIO_DIAS', '7'))
    CALIDAD_DPI_MINIMO = float(os.environ.get('CALIDAD_DPI_MINIMO', '150'))

    # =================================================================
    # SPRINT 7 (PB-12) - Copilot administrativo NL->SQL
    # LLM opcional: cualquier API compatible con OpenAI. Sin API key
    # el copilot responde con 8 plantillas deterministas (solo lectura).
    # =================================================================
    COPILOT_BASE_URL = os.environ.get(
        'COPILOT_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    COPILOT_MODEL = os.environ.get('COPILOT_MODEL', 'gpt-4o-mini')
    COPILOT_API_KEY = os.environ.get('COPILOT_API_KEY') or None
    # Timeout en segundos para la llamada al LLM
    COPILOT_TIMEOUT = float(os.environ.get('COPILOT_TIMEOUT', '15'))
    # Maximo de filas devueltas por cualquier consulta del copilot
    COPILOT_MAX_FILAS = int(os.environ.get('COPILOT_MAX_FILAS', '200'))
    # Conexion opcional de solo lectura (usuario MySQL sin permisos de
    # escritura); si no se define se usa la conexion principal
    COPILOT_DATABASE_URL = os.environ.get('COPILOT_DATABASE_URL') or None

    @staticmethod
    def init_app(app):
        """Inicializar configuración específica de la aplicación"""
        pass


class MySQLConfig(Config):
    """
    Configuración que fuerza el uso de MySQL.
    Detecta automáticamente las variables de entorno MYSQL_USER,
    MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT y MYSQL_DATABASE.
    """
    SQLALCHEMY_DATABASE_URI = get_database_url()

    @staticmethod
    def validar():
        """Verifica que las variables de entorno MySQL estén completas."""
        faltantes = [v for v in ('MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD')
                     if v not in os.environ]
        if faltantes:
            raise RuntimeError(
                'MySQLConfig requiere las variables de entorno definidas: '
                + ', '.join(faltantes)
            )


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'mysql': MySQLConfig,
    'default': DevelopmentConfig
}
