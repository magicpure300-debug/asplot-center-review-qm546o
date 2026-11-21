# -*- coding: utf-8 -*-
"""Genera planos PDF de demostracion (A1, A0, A2) para la demo del G60."""
import os
from fpdf import FPDF

SALIDA = os.path.join(os.environ.get('TEMP', '.'), 'planos_demo')
os.makedirs(SALIDA, exist_ok=True)

PLANOS = [
    ('demo_planta_baja_a1.pdf', 'A1', (594, 841), 'PLANTA BAJA', 'ARQ-001'),
    ('demo_fundaciones_a1.pdf', 'A1', (594, 841), 'FUNDACIONES', 'EST-002'),
    ('demo_galpon_estructura_a0.pdf', 'A0', (841, 1189), 'ESTRUCTURA GALPON', 'EST-003'),
    ('demo_ampliacion_a2.pdf', 'A2', (420, 594), 'AMPLIACION VIVIENDA', 'ARQ-004'),
]


def generar(nombre, formato, tamano, titulo, codigo):
    pdf = FPDF(orientation='L', unit='mm', format=(tamano[1], tamano[0]))
    pdf.set_auto_page_break(False)
    pdf.add_page()
    ancho, alto = pdf.w, pdf.h

    # Marco
    pdf.set_line_width(1.2)
    pdf.rect(10, 10, ancho - 20, alto - 20)

    # Cuadro de titulo
    pdf.set_line_width(0.4)
    pdf.rect(10, alto - 45, ancho - 20, 35)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_xy(15, alto - 40)
    pdf.cell(0, 8, 'ASPLOT CENTER', align='L')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(15, alto - 31)
    pdf.cell(0, 6, 'Plano de demostracion - %s' % titulo)
    pdf.set_xy(15, alto - 24)
    pdf.cell(0, 6, 'Codigo: %s     Formato: %s     Escala: 1:100' %
             (codigo, formato))
    pdf.set_xy(ancho - 90, alto - 30)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'REV. A - NOV 2026')

    # Planta sencilla: habitaciones y ejes
    margen = 35
    ancho_plano = ancho - 2 * margen
    alto_plano = alto - 120
    pdf.set_line_width(0.8)
    pdf.rect(margen, 25, ancho_plano, alto_plano)
    pdf.set_line_width(0.3)
    divisiones = 4
    for i in range(1, divisiones):
        x = margen + ancho_plano * i / divisiones
        pdf.line(x, 25, x, 25 + alto_plano)
    pdf.line(margen, 25 + alto_plano / 2,
             margen + ancho_plano, 25 + alto_plano / 2)

    # Cotas
    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(margen, 18)
    pdf.cell(0, 5, '%.0f m' % (ancho_plano / 40.0))
    pdf.set_xy(margen - 12, 25 + alto_plano / 2)
    pdf.cell(0, 5, '%.0f m' % (alto_plano / 40.0))

    ruta = os.path.join(SALIDA, nombre)
    pdf.output(ruta)
    return ruta


for plano in PLANOS:
    print(generar(*plano))
