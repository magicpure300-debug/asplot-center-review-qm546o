# -*- coding: utf-8 -*-
"""
Datos de demostracion para ASPLOT CENTER (Sprint 7).

Solo datos: no cambia el esquema ni el codigo de la aplicacion. Es
idempotente (si ya hay facturas no hace nada), de modo que se puede
ejecutar sobre la base de la demo sin miedo a duplicar registros.

Sirve para que el copilot (PB-12), el panel predictivo (PB-11) y los
reportes muestren numeros reales en la defensa: facturas del mes en
curso, una factura cancelada (que el copilot debe excluir), proyectos en
distintos estados, planos por tipo y un material bajo el minimo.

Uso (desde la raiz del proyecto, con el venv activo):

    python scripts/demo_datos.py

En el G60:

    cd ~/asplot && .venv/bin/python scripts/demo_datos.py
"""
import os
import sys
from datetime import date, datetime, timedelta

RUTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RUTA)
sys.path.insert(0, RUTA)

from app import create_app                                   # noqa: E402
from models import (db, Usuario, Cliente, Proyecto, TipoPlano,  # noqa: E402
                    Plano, Material, Inventario, Factura, DetalleFactura)

app = create_app()

with app.app_context():
    if Factura.query.count() > 0:
        print('Ya hay %d facturas: no se siembra nada.' % Factura.query.count())
        raise SystemExit(0)

    admin = Usuario.query.filter_by(rol='admin').first()
    if admin is None:
        print('No hay administrador; abortando.')
        raise SystemExit(1)

    hoy = date.today()
    inicio_mes = datetime(hoy.year, hoy.month, 1, 9, 0)
    mes_pasado = inicio_mes - timedelta(days=28)

    # ---- Clientes -----------------------------------------------------
    def cliente(nombre, apellido, correo, tel):
        existente = Cliente.query.filter_by(email=correo).first()
        if existente:
            return existente
        nuevo = Cliente(nombre=nombre, apellido=apellido, email=correo,
                        telefono=tel, direccion='Maturin, Monagas')
        db.session.add(nuevo)
        db.session.flush()
        return nuevo

    c1 = cliente('Constructora', 'Oriente', 'contacto@constructororiente.com',
                 '04141234567')
    c2 = cliente('Inversiones', 'Morichal', 'compras@morichal.com',
                 '04249876543')
    c3 = cliente('Ana', 'Rondon', 'ana.rondon@example.com', '04160001122')

    # ---- Tipos de plano y planos --------------------------------------
    tipos = {}
    for nombre in ('Arquitectonico', 'Estructural', 'Topografico'):
        tipo = TipoPlano.query.filter_by(nombre_tipo=nombre).first()
        if tipo is None:
            tipo = TipoPlano(nombre_tipo=nombre,
                             descripcion='Plano %s de demostracion' % nombre)
            db.session.add(tipo)
            db.session.flush()
        tipos[nombre] = tipo

    # ---- Proyectos ----------------------------------------------------
    def proyecto(cli, nombre, tipo_servicio, estado, presupuesto, dias):
        p = Proyecto(id_cliente=cli.id_cliente, nombre_proyecto=nombre,
                     descripcion='Proyecto de demostracion',
                     tipo_servicio=tipo_servicio, estado=estado,
                     presupuesto=presupuesto,
                     fecha_solicitud=datetime.now() - timedelta(days=dias))
        db.session.add(p)
        db.session.flush()
        return p

    p1 = proyecto(c1, 'Residencia Los Guaritos', 'plano', 'ejecutado', 480, 40)
    p2 = proyecto(c2, 'Galpon industrial Morichal', 'plano', 'ejecutado', 620, 22)
    p3 = proyecto(c3, 'Ampliacion vivienda Rondon', 'correccion', 'en_progreso',
                  150, 6)
    p4 = proyecto(c2, 'Levantamiento topografico parcela 14', 'topografia',
                  'solicitado', 260, 2)

    # ---- Planos -------------------------------------------------------
    def plano(proy, tipo, nombre):
        p = Plano(id_proyecto=proy.id_proyecto,
                  id_tipo_plano=tipos[tipo].id_tipo_plano,
                  id_usuario=admin.id_usuario, nombre_plano=nombre,
                  archivo='demo_%s.pdf' % nombre.lower().replace(' ', '_'))
        db.session.add(p)
        db.session.flush()
        return p

    pl1 = plano(p1, 'Arquitectonico', 'Planta baja A1')
    pl2 = plano(p1, 'Estructural', 'Fundaciones A1')
    pl3 = plano(p2, 'Estructural', 'Galpon estructura A0')
    pl4 = plano(p3, 'Arquitectonico', 'Ampliacion A2')

    # ---- Facturas + detalles -----------------------------------------
    materiales = Material.query.order_by(Material.id_material).all()
    rollo = materiales[0] if materiales else None
    tinta = materiales[1] if len(materiales) > 1 else None

    def factura(proy, fecha, estado_pago, lineas, impuesto=0.0):
        f = Factura(id_proyecto=proy.id_proyecto,
                    id_cliente=proy.id_cliente, id_usuario=admin.id_usuario,
                    fecha_factura=fecha, impuesto=impuesto, descuento=0.0,
                    total=0.0, estado_pago=estado_pago,
                    metodo_pago='transferencia' if estado_pago == 'pagada' else None,
                    notas='Factura de demostracion')
        db.session.add(f)
        db.session.flush()
        subtotal = 0.0
        for plano_ref, material_ref, descripcion, cantidad, precio in lineas:
            db.session.add(DetalleFactura(
                id_factura=f.id_factura,
                id_plano=plano_ref.id_plano if plano_ref else None,
                id_material=material_ref.id_material if material_ref else None,
                descripcion=descripcion, cantidad=cantidad,
                precio_unitario=precio, descuento=0.0))
            subtotal += cantidad * precio
        f.subtotal = subtotal
        f.total = subtotal + impuesto
        return f

    factura(p1, inicio_mes.replace(day=2), 'pagada', [
        (pl1, rollo, 'Impresion A1 planta baja', 12, 18.0),
        (pl2, rollo, 'Impresion A1 fundaciones', 6, 18.0),
        (None, tinta, 'Tinta negra plotter', 2, 24.0),
    ])
    factura(p2, inicio_mes.replace(day=5), 'pendiente', [
        (pl3, rollo, 'Impresion A0 estructura', 8, 26.0),
        (None, tinta, 'Tinta color plotter', 3, 22.0),
    ])
    factura(p3, mes_pasado.replace(day=20), 'pagada', [
        (pl4, rollo, 'Impresion A2 ampliacion', 4, 9.0),
    ])
    # Factura cancelada: el copilot debe excluirla
    factura(p2, inicio_mes.replace(day=8), 'cancelada', [
        (None, tinta, 'Tinta negra (anulada)', 5, 24.0),
    ])

    # Stock bajo el minimo para el panel de riesgo
    if rollo is not None:
        inv = Inventario.query.filter_by(id_material=rollo.id_material).first()
        if inv is not None and (inv.cantidad or 0) > 2:
            inv.cantidad = 1

    db.session.commit()
    print('Sembrado: %d facturas, %d proyectos, %d planos, %d clientes'
          % (Factura.query.count(), Proyecto.query.count(),
             Plano.query.count(), Cliente.query.count()))
