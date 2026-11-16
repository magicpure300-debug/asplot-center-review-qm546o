/*
 * ASPLOT CENTER - Sprint 8: validacion de telefonos en el navegador.
 *
 * Replica las reglas de validacion_telefono.py (11 digitos, prefijos
 * moviles vigentes y codigos de area reales). El servidor vuelve a
 * validar: esto es solo para avisar antes de enviar.
 */
(function () {
    'use strict';

    var PREFIJOS_MOVIL = {
        '0412': 'Digitel', '0422': 'Digitel',
        '0414': 'Movistar', '0424': 'Movistar',
        '0415': 'Tesan',
        '0416': 'Movilnet', '0426': 'Movilnet'
    };

    var CODIGOS_AREA = {
        '212': 'Distrito Capital', '234': 'Miranda', '235': 'Anzoategui',
        '237': 'Dependencias Federales', '238': 'Guarico', '239': 'Miranda',
        '241': 'Carabobo', '242': 'Carabobo', '243': 'Aragua',
        '244': 'Aragua', '245': 'Aragua', '246': 'Aragua',
        '247': 'Apure', '248': 'Amazonas', '249': 'Carabobo',
        '251': 'Lara', '252': 'Lara', '253': 'Lara', '254': 'Yaracuy',
        '255': 'Portuguesa', '256': 'Portuguesa', '257': 'Portuguesa',
        '258': 'Cojedes', '259': 'Falcon',
        '260': 'Zulia', '261': 'Zulia', '262': 'Zulia', '263': 'Zulia',
        '264': 'Zulia', '265': 'Zulia', '266': 'Zulia', '267': 'Zulia',
        '268': 'Falcon', '269': 'Falcon', '270': 'Zulia',
        '271': 'Merida', '272': 'Trujillo', '273': 'Barinas',
        '274': 'Merida', '275': 'Merida', '276': 'Tachira',
        '277': 'Tachira', '278': 'Apure',
        '281': 'Anzoategui', '282': 'Anzoategui', '283': 'Anzoategui',
        '285': 'Bolivar', '286': 'Bolivar', '287': 'Delta Amacuro',
        '288': 'Bolivar', '291': 'Monagas', '292': 'Monagas',
        '293': 'Sucre', '294': 'Sucre', '295': 'Nueva Esparta'
    };

    function normalizar(texto) {
        var limpio = (texto || '').replace(/[\s\-\.\(\)\/]/g, '');
        if (!limpio) {
            return { ok: false, mensaje: 'El teléfono es obligatorio.' };
        }
        if (limpio.charAt(0) === '+') {
            limpio = limpio.substring(1);
        }
        if (limpio.indexOf('0058') === 0) {
            limpio = limpio.substring(4);
        } else if (limpio.indexOf('58') === 0 && limpio.length === 12) {
            limpio = limpio.substring(2);
        }
        if (!/^\d+$/.test(limpio)) {
            return {
                ok: false,
                mensaje: 'Solo números: se permiten espacios, guiones y paréntesis.'
            };
        }
        if (limpio.length === 10 && /^[24]/.test(limpio)) {
            limpio = '0' + limpio;
        }
        if (limpio.length !== 11) {
            return {
                ok: false,
                mensaje: 'Debe tener 11 dígitos (ej. 04141917498). Van ' +
                    limpio.length + '.'
            };
        }
        if (/^(\d)\1{10}$/.test(limpio)) {
            return {
                ok: false,
                mensaje: 'No puede tener todos los dígitos iguales.'
            };
        }
        var prefijo = limpio.substring(0, 4);
        if (PREFIJOS_MOVIL[prefijo]) {
            return {
                ok: true, valor: limpio, tipo: 'movil',
                mensaje: 'Móvil ' + PREFIJOS_MOVIL[prefijo] + ' (' + prefijo + ')'
            };
        }
        if (limpio.substring(0, 2) === '02') {
            var area = limpio.substring(1, 4);
            if (CODIGOS_AREA[area]) {
                return {
                    ok: true, valor: limpio, tipo: 'fijo',
                    mensaje: 'Fijo — ' + CODIGOS_AREA[area] + ' (0' + area + ')'
                };
            }
            return {
                ok: false,
                mensaje: 'El código de área 0' + area + ' no existe en Venezuela.'
            };
        }
        return {
            ok: false,
            mensaje: 'Prefijo ' + prefijo + ' no válido: use 0412, 0414, ' +
                '0415, 0416, 0422, 0424, 0426 o un fijo 02XX.'
        };
    }

    function preparar(input) {
        var grupo = input.closest('.form-group') || input.parentNode;
        var ayuda = grupo.querySelector('[data-telefono-ayuda]');
        if (!ayuda) {
            ayuda = document.createElement('small');
            ayuda.className = 'campo-ayuda';
            ayuda.setAttribute('data-telefono-ayuda', '');
            grupo.appendChild(ayuda);
        }

        input.setAttribute('maxlength', '20');
        input.setAttribute('inputmode', 'tel');
        input.setAttribute('autocomplete', 'tel');
        if (!input.getAttribute('placeholder')) {
            input.setAttribute('placeholder', '0414-1917498');
        }

        function revisar() {
            var texto = input.value;
            if (!texto.trim()) {
                ayuda.textContent = 'Formato: 0414-1917498 (11 dígitos) o +58 414 1917498.';
                ayuda.className = 'campo-ayuda';
                if (input.required) {
                    input.setCustomValidity('El teléfono es obligatorio.');
                } else {
                    input.setCustomValidity('');
                }
                return;
            }
            var datos = normalizar(texto);
            if (datos.ok) {
                ayuda.textContent = 'Línea válida: ' + datos.mensaje + '.';
                ayuda.className = 'campo-ayuda campo-ayuda-ok';
                input.setCustomValidity('');
            } else {
                ayuda.textContent = datos.mensaje;
                ayuda.className = 'campo-ayuda campo-ayuda-error';
                input.setCustomValidity(datos.mensaje);
            }
        }

        input.addEventListener('input', revisar);
        input.addEventListener('blur', revisar);
        revisar();
    }

    function iniciar() {
        var campos = document.querySelectorAll('input[name="telefono"]');
        for (var i = 0; i < campos.length; i++) {
            preparar(campos[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }

    // Expuesto para pruebas automatizadas (Node) y depuracion.
    window.validarTelefonoVE = normalizar;
})();
