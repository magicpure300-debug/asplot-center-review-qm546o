// Verificacion del JS de telefonos sin navegador (Sprint 8).
const fs = require('fs');
const vm = require('vm');

const codigo = fs.readFileSync(process.argv[2], 'utf8');
const contexto = {
    window: {},
    document: {
        readyState: 'complete',
        querySelectorAll: () => [],
        addEventListener: () => {},
    },
};
vm.createContext(contexto);
vm.runInContext(codigo, contexto);

const validar = contexto.window.validarTelefonoVE;
const casos = [
    ['04141917498', true, '04141917498'],
    ['+58 416 1234567', true, '04161234567'],
    ['0291-1234567', true, '02911234567'],
    ['04171917498', false, null],
    ['123', false, null],
    ['00000000000', false, null],
];
let fallos = 0;
for (const [entrada, esperado, canonico] of casos) {
    const r = validar(entrada);
    const ok = r.ok === esperado && (!esperado || r.valor === canonico);
    console.log((ok ? 'OK   ' : 'FALLO') + ' ' + entrada + ' -> ' + JSON.stringify(r));
    if (!ok) fallos++;
}
console.log(fallos ? 'FALLOS: ' + fallos : 'JS DE TELEFONOS EN VERDE');
process.exit(fallos ? 1 : 0);
