# Capturas de la demo

Imágenes tomadas de la demo real (G60) el 20 de noviembre de 2026 con
Microsoft Edge headless, sesión de administrador y datos de demostración
(`scripts/demo_datos.py` + planos PDF de ejemplo).

| Archivo | Qué muestra | Historia |
|---|---|---|
| `00-landing.png` | Portada pública con la identidad «blueprint» | Diseño |
| `01-dashboard.png` | Panel del administrador: alertas, accesos rápidos y métricas (10 clientes, 6 proyectos, 4 planos, facturado $682) | General |
| `02-copilot.png` | Copilot en modo plantillas: interpretación, SQL desplegable y tabla (facturación del mes: 2 facturas, 646) | PB-12 |
| `03-inventario.png` | Predicción de reabastecimiento: velocidad, días restantes, punto de reorden, compra sugerida y estados | PB-11 |
| `04-cotizacion.png` | Cubicación automática de un PDF A1: área 0,4996 m², tarifa, insumos, margen y total sugerido | PB-10 |
| `05-calidad-plano.png` | Checklist de calidad: formato real vs. declarado, DPI, tamaño de página y legibilidad | PB-13 |
| `06-telefono.png` | Validación de teléfono en vivo: prefijo 0417 rechazado con el motivo | Sprint 8 |

## Cómo se generaron

```bash
# 1. Planos PDF de ejemplo (A1/A0/A2) — opcional, ya están en el G60
python scripts/capturas/generar_planos_demo.py

# 2. Capturas de pantalla
set ASPLOT_ADMIN_PASSWORD=...        # PowerShell: $env:ASPLOT_ADMIN_PASSWORD="..."
python scripts/capturas/capturar_demo.py http://192.168.0.101:8000/asplot docs/capturas
python scripts/capturas/capturar_detalles.py http://192.168.0.101:8000/asplot docs/capturas
```

Las capturas se tomaron con Edge headless y CDP contra la LAN del G60
(`http://192.168.0.101:8000/asplot`), iniciando sesión como administrador.
Los planos de ejemplo se generaron con `fpdf2` en formato A1/A0/A2 y se
subieron a `static/uploads/planos/`. Los scripts leen el correo y la clave
del administrador de `ASPLOT_ADMIN_EMAIL` y `ASPLOT_ADMIN_PASSWORD`; no
contienen credenciales.

> Las credenciales de la demo no se incluyen en el repositorio.

## Uso

- Respaldo para la defensa si falla el servidor o el internet.
- Evidencia visual para el mirror de revisión y el ERS.
- Material para el guion (`docs/GUION_DEFENSA.md`).
