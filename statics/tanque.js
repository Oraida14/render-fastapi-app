const { useOptimistic } = require("react");

const labelMappings = {
//    'ultimo3': { campo: 'Presion_Instantanea', sitio: 'p263', texto: 'Presión: ', circulo: 'circle-263' },
//    'ultimo4': { campo: 'Gasto_Instantaneo', sitio: 'p263', texto: 'Gasto: ', circulo: 'circle-263' },
    'ultimo7': { campo: 'Nivel_1', sitio: 'tanque3cantos', texto: 'Nivel: ' },
    'ultimo8': { campo: 'Gasto_Instantaneo', sitio: 'tanque3cantos', texto: 'Q= Entrada: ' },
    'ultimo10': { campo: 'Gasto_Instantaneo', sitio: 'tanque3cantos', texto: 'Q= Salida: ' },
//    'ultimo11': { campo: 'Presion_Instantanea', sitio: 'reb_62', texto: 'Presión: ', circulo: 'circle-reb_62' },
//    'ultimo12': { campo: 'Gasto_Instantaneo', sitio: 'reb_62', texto: 'Gasto: ', circulo: 'circle-reb_62' },
 //   'ultimo13': { campo: 'Presion_Instantanea', sitio: 'p25', texto: 'Presión: ', circulo: 'circle-25-R' },
//    'ultimo14': { campo: 'Gasto_Instantaneo', sitio: 'p25', texto: 'Gasto: ', circulo: 'circle-25-R' },
//    'ultimo15': { campo: 'Presion_Instantanea', sitio: 'reb_62A', texto: 'Presión: ', circulo: 'circle-reb_62A' },
 //   'ultimo16': { campo: 'Gasto_Instantaneo', sitio: 'reb_62A', texto: 'Gasto: ', circulo: 'circle-reb_62A' }
};

const MAX_CYLINDER_HEIGHT = 5;  // Máximo nivel de agua (en metros)
const MIN_CYLINDER_HEIGHT = 0;   // Mínimo nivel de agua (en metros)
const CRITICAL_GASTO = 4.5;        // Límite crítico para gasto
const CRITICAL_PRESION = 2;      // Límite crítico para presión

async function fetchCSVData() {
    const response = await fetch('datos_pozos.csv');
    const csvText = await response.text();
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');

    return lines.slice(1).map(line => {
        const values = line.split(',');
        const entry = {};
        headers.forEach((header, i) => {
            entry[header.trim()] = values[i]?.trim();
        });
        return entry;
    });
}





async function updateLabels() {
    const data = await fetchCSVData();
    const siteValues = {};

    Object.entries(labelMappings).forEach(([id, config]) => {
        const label = document.getElementById(id);
        const siteData = data.find(d => d.nombre_sitio === config.sitio);

        if (siteData && config.campo in siteData) {
            const valor = siteData[config.campo];
            label.innerText = config.texto + valor;

            if (config.circulo) {
                if (!siteValues[config.sitio]) siteValues[config.sitio] = {};
                siteValues[config.sitio][config.campo] = parseFloat(valor);
            }

            // Si es etiqueta de nivel, ajusta el cilindro
            if (id === 'ultimo7') {
                ajustarCilindro(parseFloat(valor));
            }

        } else {
            label.innerText = config.texto + 'N/A';
        }
    });

    Object.entries(siteValues).forEach(([sitio, valores]) => {
        const mapeo = Object.values(labelMappings).find(e => e.sitio === sitio && e.circulo);
        if (mapeo) {
            const circle = document.getElementById(mapeo.circulo);
            if (!circle) return;

            const gasto = valores['Gasto_Instantaneo'] ?? 1;
            const presion = valores['Presion_Instantanea'] ?? 1;

            // Cambiar colores si los valores superan los límites
            if (gasto === 0 || presion === 0 || gasto > CRITICAL_GASTO || presion > CRITICAL_PRESION) {
                circle.classList.remove('green');
                circle.classList.add('red', 'blink');
            } else {
                circle.classList.remove('red', 'blink');
                circle.classList.add('green');
            }
        }
    });
}

function ajustarCilindro(nivel) {
    const cilindro = document.getElementById('cilindroNivel');
    const alerta = document.getElementById('alertaNivel');
    const datoNivel = document.getElementById('datoNivel');

    const maxAltura = 47; // en vh
    const nuevoNivel = Math.min(Math.max(nivel, MIN_CYLINDER_HEIGHT), MAX_CYLINDER_HEIGHT);
    const nuevaAltura = (nuevoNivel / MAX_CYLINDER_HEIGHT) * maxAltura;

    cilindro.style.height = `${nuevaAltura}vh`;

    // Posicionar el texto justo arriba del llenado
    const baseBottom = 10; // debe coincidir con el "bottom" del cilindro en vh
    const topTexto = -2;(baseBottom + nuevaAltura) + 5; // +2 para separarlo un poco
    datoNivel.style.top = `${topTexto}vh`;

    // Cambiar color del cilindro según nivel
    if (nuevoNivel < 2) {
        cilindro.style.backgroundColor = 'rgba(255, 17, 0, 0.6)';
        alerta.style.display = 'block';
    } else if (nuevoNivel < 4.5) {
        cilindro.style.backgroundColor = 'rgba(0, 110, 255, 0.62)';
        alerta.style.display = 'none';
    } else {
        cilindro.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
        alerta.style.display = 'none';
    }

    datoNivel.innerText = `Nivel: ${nuevoNivel.toFixed(1)} m`;
}



// Primera carga y actualización periódica
updateLabels();
setInterval(updateLabels, 30000);
