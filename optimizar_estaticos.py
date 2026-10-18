# -*- coding: utf-8 -*-
"""
=============================================================================
 ASPLOT CENTER - Sprint 3 (PB-07)
 Optimización de recursos estáticos de imagen
=============================================================================
 Comprime las imágenes de `static/images` sin pérdida visual apreciable
 y genera una versión WebP (mucho más ligera) junto al original, para que
 las plantillas puedan usar <picture> con fallback.

 Acciones:
   1. Recodifica los PNG con optimización (reduce metadata y paleta).
   2. Genera la versión .webp equivalente (calidad 82).
   3. Reporta el ahorro de peso por archivo.

 No sobrescribe el original si la versión optimizada es MAYOR que el
 original (se conserva siempre el archivo más ligero).

 Uso:
   python optimizar_estaticos.py              # optimiza static/images
   python optimizar_estaticos.py --carpeta X  # otra carpeta
   python optimizar_estaticos.py --calidad 85 # calidad WebP personalizada
=============================================================================
"""

import argparse
import os
import sys

EXTENSIONES = {'.png', '.jpg', '.jpeg'}


def optimizar_carpeta(carpeta, calidad_webp=82):
    try:
        from PIL import Image
    except ImportError:
        print('[ERROR] Pillow no está instalado. Ejecute: pip install pillow')
        sys.exit(1)

    if not os.path.isdir(carpeta):
        print(f'[ERROR] No existe la carpeta: {carpeta}')
        return

    archivos = sorted(
        os.path.join(carpeta, f) for f in os.listdir(carpeta)
        if os.path.splitext(f)[1].lower() in EXTENSIONES
    )
    if not archivos:
        print(f'[INFO] Sin imágenes en {carpeta}')
        return

    print('=' * 70)
    print(' ASPLOT CENTER - Optimización de estáticos (Sprint 3 / PB-07)')
    print('=' * 70)
    print(f'\n{"ARCHIVO":<34} {"ANTES":>9} {"DESPUÉS":>9} {"AHORRO":>8}')
    print('-' * 70)

    total_antes = total_despues = 0
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        antes = os.path.getsize(ruta)
        total_antes += antes
        despues = antes

        try:
            with Image.open(ruta) as img:
                img.load()

                # 1) Recodificación optimizada del original
                tmp = ruta + '.tmp'
                if img.mode in ('RGBA', 'LA', 'P'):
                    # PNG conserva transparencia
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    img.save(tmp, format='PNG', optimize=True)
                else:
                    img = img.convert('RGB')
                    img.save(tmp, format='JPEG', quality=88, optimize=True)

                if os.path.getsize(tmp) < antes:
                    os.replace(tmp, ruta)
                    despues = os.path.getsize(ruta)
                else:
                    os.remove(tmp)  # el original ya era más ligero

                # 2) Versión WebP junto al original
                webp = os.path.splitext(ruta)[0] + '.webp'
                with Image.open(ruta) as img2:
                    img2.save(webp, format='WEBP', quality=calidad_webp, method=6)
                webp_peso = os.path.getsize(webp)

                ahorro = (1 - despues / antes) * 100 if antes else 0
                ahorro_webp = (1 - webp_peso / antes) * 100 if antes else 0
                base = os.path.splitext(nombre)[0]
                print(f'{nombre:<34} {antes/1024:>7.0f}K {despues/1024:>7.0f}K '
                      f'{ahorro:>7.0f}%')
                print(f'  {base}.webp (WebP){" " * 12} {webp_peso/1024:>7.0f}K '
                      f'{ahorro_webp:>7.0f}%')

                total_despues += despues
        except Exception as e:
            print(f'{nombre:<34} error: {e}')

    print('-' * 70)
    if total_antes:
        ahorro_total = (1 - total_despues / total_antes) * 100
        print(f'{"TOTAL originales":<34} {total_antes/1024:>7.0f}K '
              f'{total_despues/1024:>7.0f}K {ahorro_total:>7.0f}%')
    print('\nLas versiones .webp pueden usarse en <picture> con fallback al original.')


def main():
    parser = argparse.ArgumentParser(description='Optimización de estáticos (Sprint 3 - PB-07)')
    parser.add_argument('--carpeta', default=os.path.join('static', 'images'),
                        help='Carpeta con imágenes (por defecto: static/images)')
    parser.add_argument('--calidad', type=int, default=82, help='Calidad WebP (1-100)')
    args = parser.parse_args()
    optimizar_carpeta(args.carpeta, args.calidad)


if __name__ == '__main__':
    main()
