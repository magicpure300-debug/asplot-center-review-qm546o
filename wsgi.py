# -*- coding: utf-8 -*-
"""
Punto de entrada WSGI para servidores de producción.

Uso con gunicorn (Render, Linux):
    gunicorn wsgi:app

UWSGI (PythonAnywhere) apunta también a este objeto `app`.
En desarrollo local se sigue usando: python app.py
"""
from app import create_app

app = create_app()
