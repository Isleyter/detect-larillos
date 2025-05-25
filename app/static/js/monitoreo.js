function startMonitoring() {
    if (!monitorInterval) {
        fetch('/start_monitoring', {method: 'POST'})
            .then(response => console.log('Monitoreo iniciado'))
            .catch(error => console.error('Error iniciando monitoreo:', error));
        monitorInterval = setInterval(updateCounts, 1000);
    }
}

function stopMonitoring() {
    if (monitorInterval) {
        clearInterval(monitorInterval);
        monitorInterval = null;
        fetch('/stop_monitoring', {method: 'POST'})
            .then(response => console.log('Monitoreo detenido'))
            .catch(error => console.error('Error deteniendo monitoreo:', error));
    }
}

/*--------------monitoreo conte en tiempo real con ajax 
let monitorInterval;

function startMonitoring() {
    if (!monitorInterval) {
        fetch('/start_monitoring', { method: 'POST' });
        monitorInterval = setInterval(updateCounts, 1000);
    }
}

function stopMonitoring() {
    if (monitorInterval) {
        fetch('/stop_monitoring', { method: 'POST' });
        clearInterval(monitorInterval);
        monitorInterval = null;
    }
}

function updateCounts() {
    fetch('/conteo')
        .then(response => response.json())
        .then(data => {
            const malos = data.fisuras + data.roturas;

            document.getElementById('total').textContent = data.total;
            document.getElementById('buenos').textContent = data.buenos;
            document.getElementById('malos').textContent = malos;
        })
        .catch(error => console.error('Error al obtener conteo:', error));
}
*/
