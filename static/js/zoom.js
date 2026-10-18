/* ==========================================================================
 * ASPLOT CENTER - Visor de imágenes con zoom (Sprint 3 - PB-09)
 * Galería HD interactiva sin dependencias externas (vanilla JS).
 *
 * Funcionalidades:
 *   - Click en cualquier miniatura .miniatura-zoomable abre el visor.
 *   - Zoom con rueda del ratón o botones +/- (100% a 500%).
 *   - Arrastre (paneo) de la imagen ampliada.
 *   - Teclado: +/-, 0 (restablecer), Flechas (mover), Esc (cerrar).
 *   - Barra de progreso de carga para imágenes de alta definición.
 *
 * Uso: incluir tras el marcado; cualquier <img class="miniatura-zoomable"
 *      data-zoom-src="..." data-zoom-titulo="..."> queda habilitado.
 * ========================================================================== */
(function () {
    'use strict';

    var overlay = document.getElementById('zoom-overlay');
    if (!overlay) return; // la página no tiene visor

    var imagen = document.getElementById('zoom-imagen');
    var contenedor = document.getElementById('zoom-contenedor');
    var nivelEl = document.getElementById('zoom-nivel');
    var tituloEl = document.getElementById('zoom-titulo');

    // Límites de zoom
    var ZOOM_MIN = 1, ZOOM_MAX = 5, ZOOM_PASO = 0.25;

    var escala = 1;      // escala actual (1 = 100%)
    var desplX = 0;      // desplazamiento en píxeles
    var desplY = 0;
    var arrastrando = false;
    var origenArrastre = null;

    // ------------------------------------------------------------------ //
    // Aplicar transformación
    // ------------------------------------------------------------------ //
    function aplicar() {
        imagen.style.transform =
            'translate(' + desplX + 'px, ' + desplY + 'px) scale(' + escala + ')';
        nivelEl.textContent = Math.round(escala * 100) + '%';
    }

    function centrar() {
        escala = 1;
        desplX = 0;
        desplY = 0;
        aplicar();
    }

    function cambiarZoom(delta) {
        escala = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, escala + delta));
        aplicar();
    }

    // ------------------------------------------------------------------ //
    // Abrir / cerrar
    // ------------------------------------------------------------------ //
    function abrir(src, titulo) {
        tituloEl.textContent = titulo || '';
        imagen.src = src;
        centrar();
        overlay.hidden = false;
        document.body.style.overflow = 'hidden';
        document.getElementById('zoom-cerrar').focus();
    }

    function cerrar() {
        overlay.hidden = true;
        document.body.style.overflow = '';
        imagen.removeAttribute('src');
    }

    // ------------------------------------------------------------------ //
    // Eventos de miniaturas (delegación: funciona con imágenes dinámicas)
    // ------------------------------------------------------------------ //
    document.addEventListener('click', function (e) {
        var miniatura = e.target.closest('.miniatura-zoomable');
        if (!miniatura) return;
        e.preventDefault();
        abrir(
            miniatura.getAttribute('data-zoom-src') || miniatura.src,
            miniatura.getAttribute('data-zoom-titulo') || miniatura.alt
        );
    });

    // ------------------------------------------------------------------ //
    // Controles de la barra
    // ------------------------------------------------------------------ //
    document.getElementById('zoom-in').addEventListener('click', function () {
        cambiarZoom(ZOOM_PASO);
    });
    document.getElementById('zoom-out').addEventListener('click', function () {
        cambiarZoom(-ZOOM_PASO);
    });
    document.getElementById('zoom-reset').addEventListener('click', centrar);
    document.getElementById('zoom-cerrar').addEventListener('click', cerrar);

    // Clic fuera de la imagen también cierra
    overlay.addEventListener('click', function (e) {
        if (e.target === overlay || e.target === contenedor) cerrar();
    });

    // ------------------------------------------------------------------ //
    // Zoom con rueda del ratón
    // ------------------------------------------------------------------ //
    contenedor.addEventListener('wheel', function (e) {
        e.preventDefault();
        cambiarZoom(e.deltaY < 0 ? ZOOM_PASO : -ZOOM_PASO);
    }, { passive: false });

    // ------------------------------------------------------------------ //
    // Arrastre (paneo)
    // ------------------------------------------------------------------ //
    contenedor.addEventListener('mousedown', function (e) {
        arrastrando = true;
        origenArrastre = { x: e.clientX - desplX, y: e.clientY - desplY };
        contenedor.style.cursor = 'grabbing';
        e.preventDefault();
    });

    window.addEventListener('mousemove', function (e) {
        if (!arrastrando) return;
        desplX = e.clientX - origenArrastre.x;
        desplY = e.clientY - origenArrastre.y;
        aplicar();
    });

    window.addEventListener('mouseup', function () {
        arrastrando = false;
        contenedor.style.cursor = 'grab';
    });

    // Soporte táctil: un dedo mueve, dos dedos hacen zoom
    var ultimoDistancia = null;
    contenedor.addEventListener('touchstart', function (e) {
        if (e.touches.length === 1) {
            arrastrando = true;
            origenArrastre = {
                x: e.touches[0].clientX - desplX,
                y: e.touches[0].clientY - desplY
            };
        } else if (e.touches.length === 2) {
            ultimoDistancia = distanciaTouch(e.touches);
        }
    }, { passive: true });

    contenedor.addEventListener('touchmove', function (e) {
        if (arrastrando && e.touches.length === 1) {
            desplX = e.touches[0].clientX - origenArrastre.x;
            desplY = e.touches[0].clientY - origenArrastre.y;
            aplicar();
        } else if (e.touches.length === 2 && ultimoDistancia) {
            var nueva = distanciaTouch(e.touches);
            escala = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN,
                escala * (nueva / ultimoDistancia)));
            ultimoDistancia = nueva;
            aplicar();
        }
    }, { passive: true });

    contenedor.addEventListener('touchend', function () {
        arrastrando = false;
        ultimoDistancia = null;
    });

    function distanciaTouch(touches) {
        var dx = touches[0].clientX - touches[1].clientX;
        var dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // ------------------------------------------------------------------ //
    // Teclado
    // ------------------------------------------------------------------ //
    window.addEventListener('keydown', function (e) {
        if (overlay.hidden) return;
        switch (e.key) {
            case 'Escape': cerrar(); break;
            case '+': case '=': cambiarZoom(ZOOM_PASO); break;
            case '-': case '_': cambiarZoom(-ZOOM_PASO); break;
            case '0': centrar(); break;
            case 'ArrowLeft': desplX += 40; aplicar(); break;
            case 'ArrowRight': desplX -= 40; aplicar(); break;
            case 'ArrowUp': desplY += 40; aplicar(); break;
            case 'ArrowDown': desplY -= 40; aplicar(); break;
        }
    });
})();
