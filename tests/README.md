# Pruebas automatizadas

Cada archivo crea una copia limpia del proyecto en la carpeta temporal, con
su propia base SQLite, y ejecuta las comprobaciones de su sprint. No tocan la
base real ni el `instance/` del proyecto.

| Archivo | Qué cubre | Comprobaciones |
|---|---|---|
| `test_sprint5.py` | cotización automática (PB-10) | 26 |
| `test_sprint6.py` | inventario predictivo y calidad de planos (PB-11, PB-13) | 31 |
| `test_sprint7.py` | copilot NL→SQL (PB-12) | 63 |
| `test_sprint8.py` | validación de teléfonos | 61 |
| `test_diseno_smoke.py` | sistema de diseño «blueprint» | smoke |
| `test_telefono_js.js` | misma regla de teléfonos en el navegador (Node) | 6 casos |

## Cómo ejecutarlas

Desde la raíz del proyecto, con el entorno virtual activo:

```bash
python tests/test_sprint8.py
```

La prueba del JavaScript necesita Node:

```bash
node tests/test_telefono_js.js static/js/telefono.js
```

En el G60 (Termux):

```bash
cd ~/asplot
ASPLOT_ORIGEN="$HOME/asplot" .venv/bin/python tests/test_sprint8.py
```

La variable `ASPLOT_ORIGEN` permite apuntar a otra copia del proyecto. Si no
se define, se usa la ruta del equipo de desarrollo.

## Resultado esperado

Cada suite imprime `OK` por comprobación y termina con:

```text
RESULTADO: TODAS LAS PRUEBAS EN VERDE
```

y código de salida `0`. Con fallos, lista las comprobaciones y sale con `1`.
