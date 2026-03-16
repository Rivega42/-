// State
let currentUser = null;
let currentScreen = 'welcome-screen';
let previousScreen = null;
let reservedBooks = [];
let allCells = [];
let currentRow = 'FRONT';
let ws = null;

// WebSocket
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        loadSystemStatus();
    };
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
    ws.onerror = (e) => console.error('WebSocket error:', e);
    
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
    };
}

function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'progress':
            updateProgress(msg.data);
            break;
        case 'error':
            showError(msg.data?.message || msg.message);
            break;
        case 'card_read':
            authenticate(msg.data.uid);
            break;
        case 'sensors':
            updateSensorsDisplay(msg.data);
            break;
        case 'position':
            updatePositionDisplay(msg);
            break;
    }
}

// API
async function api(method, endpoint, data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) options.body = JSON.stringify(data);
    
    try {
        const response = await fetch(endpoint, options);
        return response.json();
    } catch (e) {
        console.error('API error:', e);
        return { success: false, error: 'Ошибка соединения' };
    }
}

// System Status
async function loadSystemStatus() {
    const status = await api('GET', '/api/status');
    if (status) {
        document.getElementById('status-irbis').textContent = 
            `ИРБИС: ${status.irbisConnected ? '✅' : '❌'}`;
        document.getElementById('status-cells').textContent = 
            `Ячеек: ${status.statistics?.occupiedCells || 0}/${status.statistics?.totalCells || 126}`;
    }
}

// Authentication
async function authenticate(rfid) {
    showScreen('progress-screen');
    setProgress(50, 'Авторизация...');
    
    const result = await api('POST', '/api/auth/card', { rfid });
    
    if (result.success) {
        currentUser = result.user;
        reservedBooks = result.reservedBooks || [];
        
        updateUserInfo();
        
        switch (currentUser.role) {
            case 'admin':
                showScreen('admin-menu');
                updateExtractionAlert(result.needsExtraction, 'admin-extraction');
                break;
            case 'librarian':
                showScreen('librarian-menu');
                updateExtractionAlert(result.needsExtraction, 'extraction');
                break;
            default:
                showScreen('reader-menu');
        }
    } else {
        showError(result.error || 'Ошибка авторизации');
    }
}

function logout() {
    currentUser = null;
    reservedBooks = [];
    showScreen('welcome-screen');
}

// UI Updates
function updateUserInfo() {
    const roleNames = { admin: 'Админ', librarian: 'Библиотекарь', reader: 'Читатель' };
    const info = `${currentUser.name} (${roleNames[currentUser.role] || currentUser.role})`;
    
    ['user-info', 'librarian-info', 'admin-info'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = info;
    });
    
    document.getElementById('reserved-count').textContent = `${reservedBooks.length} забронировано`;
}

function updateExtractionAlert(count, prefix = 'extraction') {
    const alert = document.getElementById(`${prefix}-alert`);
    const countEl = document.getElementById(`${prefix}-count`);
    if (alert && countEl) {
        if (count > 0) {
            countEl.textContent = count;
            alert.classList.remove('hidden');
        } else {
            alert.classList.add('hidden');
        }
    }
}

function updateBooksList() {
    const container = document.getElementById('books-container');
    
    if (reservedBooks.length === 0) {
        container.innerHTML = `
            <div class="center-content">
                <div class="icon-lg">📚</div>
                <p>Нет забронированных книг</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = reservedBooks.map(book => `
        <div class="list-item" data-testid="book-item-${book.rfid}">
            <div>
                <h4>${book.title}</h4>
                <p>${book.author || 'Автор неизвестен'}</p>
            </div>
            <button class="btn btn-primary" onclick="issueBook('${book.rfid}')" data-testid="btn-issue-${book.rfid}">
                📖 Забрать
            </button>
        </div>
    `).join('');
}

// Operations
async function issueBook(bookRfid) {
    showScreen('progress-screen');
    setProgress(20, 'Выдача книги...');
    
    const result = await api('POST', '/api/issue', {
        bookRfid,
        userRfid: currentUser.rfid
    });
    
    if (result.success) {
        reservedBooks = reservedBooks.filter(b => b.rfid !== bookRfid);
        showSuccess(result.message);
    } else {
        showError(result.error);
    }
}

function startReturn() {
    showScreen('return-book');
    document.getElementById('return-rfid').value = '';
    document.getElementById('return-rfid').focus();
}

async function returnBook() {
    const rfid = document.getElementById('return-rfid').value.trim();
    if (!rfid) {
        alert('Введите или отсканируйте RFID книги');
        return;
    }
    
    showScreen('progress-screen');
    setProgress(30, 'Возврат книги...');
    
    const result = await api('POST', '/api/return', { bookRfid: rfid });
    
    if (result.success) {
        showSuccess(result.message);
    } else {
        showError(result.error);
    }
}

async function loadBook() {
    const rfid = document.getElementById('load-rfid').value.trim();
    const title = document.getElementById('load-title').value.trim();
    const author = document.getElementById('load-author').value.trim();
    
    if (!rfid || !title) {
        alert('Заполните RFID и название книги');
        return;
    }
    
    showScreen('progress-screen');
    setProgress(30, 'Загрузка книги...');
    
    const result = await api('POST', '/api/load-book', {
        bookRfid: rfid,
        title,
        author: author || undefined
    });
    
    if (result.success) {
        document.getElementById('load-rfid').value = '';
        document.getElementById('load-title').value = '';
        document.getElementById('load-author').value = '';
        showSuccess(result.message);
    } else {
        showError(result.error);
    }
}

async function extractAll() {
    showScreen('progress-screen');
    setProgress(20, 'Изъятие всех книг...');
    
    const result = await api('POST', '/api/extract-all', {});
    
    if (result.success) {
        showSuccess(`Изъято ${result.extracted} книг`);
    } else {
        showError(result.error || 'Ошибка изъятия');
    }
}

async function runInventory() {
    showScreen('progress-screen');
    setProgress(10, 'Инвентаризация...');
    
    const result = await api('POST', '/api/run-inventory', {});
    showSuccess(`Найдено ${result.found} книг, отсутствует ${result.missing}`);
}

// Cells View
async function loadCells() {
    const filter = document.getElementById('cells-filter')?.value || 'all';
    const result = await api('GET', '/api/cells');
    
    if (Array.isArray(result)) {
        allCells = result;
        renderCellsGrid();
    }
}

function switchRow(row) {
    currentRow = row;
    document.querySelectorAll('.row-tabs .tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent.includes(row === 'FRONT' ? 'Передний' : 'Задний'));
    });
    renderCellsGrid();
}

function renderCellsGrid() {
    const grid = document.getElementById('cells-grid');
    if (!grid) return;
    
    const filter = document.getElementById('cells-filter')?.value || 'all';
    const rowCells = allCells.filter(c => c.row === currentRow);
    
    // Build 3x21 grid (3 columns, 21 rows)
    let html = '';
    for (let y = 0; y < 21; y++) {
        for (let x = 0; x < 3; x++) {
            const cell = rowCells.find(c => c.x === x && c.y === y);
            
            if (!cell) {
                html += `<div class="cell empty" style="opacity:0.3">${x}-${y}</div>`;
                continue;
            }
            
            // Apply filter
            if (filter !== 'all') {
                if (filter === 'occupied' && cell.status !== 'occupied') {
                    html += `<div class="cell" style="opacity:0.2">${x}-${y}</div>`;
                    continue;
                }
                if (filter === 'empty' && cell.status !== 'empty') {
                    html += `<div class="cell" style="opacity:0.2">${x}-${y}</div>`;
                    continue;
                }
                if (filter === 'extraction' && !cell.needs_extraction) {
                    html += `<div class="cell" style="opacity:0.2">${x}-${y}</div>`;
                    continue;
                }
            }
            
            let className = 'cell ' + cell.status;
            if (cell.needs_extraction) className += ' extraction';
            
            const title = cell.book_title || 'Пустая ячейка';
            html += `<div class="${className}" onclick="showCellDetails(${cell.id})" title="${title}" data-testid="cell-${cell.id}">${x}-${y}</div>`;
        }
    }
    
    grid.innerHTML = html || '<p>Нет данных о ячейках</p>';
    
    // Update stats
    const occupied = allCells.filter(c => c.status === 'occupied').length;
    const extraction = allCells.filter(c => c.needs_extraction).length;
    const empty = allCells.length - occupied;
    
    const details = document.getElementById('cell-details');
    if (details && !details.classList.contains('hidden')) return;
    
    if (details) {
        details.classList.remove('hidden');
        details.innerHTML = `
            <h4>Статистика ряда ${currentRow === 'FRONT' ? 'Передний' : 'Задний'}</h4>
            <p>Занято: ${occupied} | Свободно: ${empty} | Требуют изъятия: ${extraction}</p>
        `;
    }
}

function showCellDetails(cellId) {
    const cell = allCells.find(c => c.id === cellId);
    if (!cell) return;
    
    const details = document.getElementById('cell-details');
    details.classList.remove('hidden');
    details.innerHTML = `
        <h4>Ячейка ${cell.row} ${cell.x}-${cell.y}</h4>
        <p>Статус: ${cell.status}</p>
        ${cell.book_title ? `<p>Книга: ${cell.book_title}</p>` : ''}
        ${cell.needs_extraction ? '<p style="color:var(--warning)">⚠️ Требует изъятия</p>' : ''}
        ${cell.status === 'occupied' ? `<button class="btn btn-sm btn-primary" onclick="extractCell(${cell.id})">Изъять</button>` : ''}
    `;
}

async function extractCell(cellId) {
    showScreen('progress-screen');
    setProgress(20, 'Изъятие книги...');
    
    const result = await api('POST', '/api/extract', { cellId });
    
    if (result.success) {
        showSuccess(result.message);
        loadCells();
    } else {
        showError(result.error);
    }
}

// Operations Log
async function loadOperations() {
    const filter = document.getElementById('log-filter')?.value || 'all';
    const result = await api('GET', `/api/operations?limit=100&filter=${filter}`);
    
    const list = document.getElementById('operations-list');
    if (!list) return;
    
    if (!result || result.length === 0) {
        list.innerHTML = '<p class="center-content">Нет операций</p>';
        return;
    }
    
    list.innerHTML = result.map(op => `
        <div class="list-item">
            <div>
                <h4>${op.operation}</h4>
                <p>${op.timestamp} | ${op.book_rfid || ''} | ${op.result}</p>
            </div>
        </div>
    `).join('');
}

// Statistics
async function showStatistics() {
    showScreen('statistics');
    const stats = await api('GET', '/api/statistics');
    
    if (stats) {
        document.getElementById('stat-occupied').textContent = stats.occupiedCells || 0;
        document.getElementById('stat-empty').textContent = (stats.totalCells - stats.occupiedCells) || 0;
        document.getElementById('stat-extraction').textContent = stats.booksNeedExtraction || 0;
        document.getElementById('stat-issues-today').textContent = stats.issuesToday || 0;
        document.getElementById('stat-returns-today').textContent = stats.returnsToday || 0;
        document.getElementById('stat-total-issues').textContent = stats.issuesTotal || 0;
    }
}

// Calibration
async function loadCalibration() {
    const result = await api('GET', '/api/calibration');
    if (result) {
        // Load X positions
        for (let i = 0; i < 3; i++) {
            const el = document.getElementById(`cal-x-${i}`);
            if (el && result.positions?.x?.[i] !== undefined) {
                el.value = result.positions.x[i];
            }
        }
        
        // Generate Y positions
        const container = document.getElementById('calibration-y-positions');
        if (container && result.positions?.y) {
            let html = '';
            for (let i = 0; i < 21; i++) {
                html += `
                    <div class="calibration-row">
                        <label>Ряд ${i}:</label>
                        <input type="number" id="cal-y-${i}" value="${result.positions.y[i] || i * 450}">
                        <button class="btn btn-sm" onclick="testPosition('y', ${i})">Тест</button>
                    </div>
                `;
            }
            container.innerHTML = html;
        }
        
        // Update current position display
        if (result.kinematics) {
            console.log('Kinematics:', result.kinematics);
        }
    }
}

async function testPosition(axis, index) {
    const input = document.getElementById(`cal-${axis}-${index}`);
    const value = parseInt(input?.value || 0);
    
    showScreen('progress-screen');
    setProgress(50, `Тест позиции ${axis.toUpperCase()}=${value}...`);
    
    const result = await api('POST', '/api/calibration/test', { axis, index, value });
    
    if (result.success) {
        showSuccess(`Позиция ${axis.toUpperCase()}=${value} достигнута`);
    } else {
        showError(result.error || 'Ошибка перемещения');
    }
}

async function manualMove() {
    const x = parseInt(document.getElementById('manual-x')?.value || 0);
    const y = parseInt(document.getElementById('manual-y')?.value || 0);
    
    showScreen('progress-screen');
    setProgress(50, `Перемещение к X=${x}, Y=${y}...`);
    
    const result = await api('POST', '/api/move', { x, y });
    
    if (result.success) {
        showSuccess(`Позиция: X=${result.position?.x || 0}, Y=${result.position?.y || 0}`);
        document.getElementById('manual-x').value = result.position?.x || 0;
        document.getElementById('manual-y').value = result.position?.y || 0;
    } else {
        showError(result.error || 'Ошибка перемещения');
    }
}

async function homePosition() {
    showScreen('progress-screen');
    setProgress(50, 'Возврат домой...');
    
    const result = await api('POST', '/api/init', {});
    if (result.success) {
        showSuccess('Система в начальной позиции');
    } else {
        showError(result.error || 'Ошибка');
    }
}

async function saveCalibration() {
    const positions = { x: [], y: [] };
    
    for (let i = 0; i < 3; i++) {
        positions.x.push(parseInt(document.getElementById(`cal-x-${i}`)?.value || 0));
    }
    
    for (let i = 0; i < 21; i++) {
        positions.y.push(parseInt(document.getElementById(`cal-y-${i}`)?.value || 0));
    }
    
    const result = await api('POST', '/api/calibration', { positions });
    if (result.success) {
        alert('Калибровка сохранена');
    } else {
        alert('Ошибка сохранения');
    }
}

async function resetCalibration() {
    if (confirm('Сбросить калибровку на значения по умолчанию?')) {
        await api('POST', '/api/calibration/reset', {});
        loadCalibration();
    }
}

// Diagnostics
async function runDiagnostics() {
    const status = await api('GET', '/api/diagnostics');
    
    if (status) {
        // Sensors with real-time data
        const sensors = document.getElementById('sensors-status');
        if (sensors) {
            const sensorNames = {
                'x_begin': 'X начало',
                'x_end': 'X конец',
                'y_begin': 'Y начало', 
                'y_end': 'Y конец',
                'tray_begin': 'Лоток втянут',
                'tray_end': 'Лоток выдвинут',
                'shelf_sensor': 'Датчик полки',
            };
            sensors.innerHTML = Object.entries(status.sensors || {}).map(([name, value]) => `
                <div class="status-item-diag">
                    <span class="status-dot ${value ? 'ok' : 'warning'}"></span>
                    <span>${sensorNames[name] || name}: ${value ? 'Активен' : 'Неактивен'}</span>
                </div>
            `).join('');
        }
        
        // Motors with current position
        const motors = document.getElementById('motors-status');
        if (motors) {
            motors.innerHTML = `
                <div class="status-item-diag">
                    <span class="status-dot ok"></span>
                    <span>Позиция X: ${status.position?.x || 0} шагов</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ok"></span>
                    <span>Позиция Y: ${status.position?.y || 0} шагов</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ok"></span>
                    <span>Лоток: ${status.position?.tray || 0} шагов</span>
                </div>
            `;
        }
        
        // Locks and shutters
        const locks = document.getElementById('locks-status');
        if (locks) {
            const stateLabels = { 'closed': 'Закрыт', 'open': 'Открыт', 'unknown': 'Неизвестно' };
            locks.innerHTML = `
                <div class="status-item-diag">
                    <span class="status-dot ${status.servos?.lock1 === 'closed' ? 'ok' : 'warning'}"></span>
                    <span>Замок 1: ${stateLabels[status.servos?.lock1] || status.servos?.lock1}</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ${status.servos?.lock2 === 'closed' ? 'ok' : 'warning'}"></span>
                    <span>Замок 2: ${stateLabels[status.servos?.lock2] || status.servos?.lock2}</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ${status.shutters?.outer === 'closed' ? 'ok' : 'warning'}"></span>
                    <span>Внешняя шторка: ${stateLabels[status.shutters?.outer] || status.shutters?.outer}</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ${status.shutters?.inner === 'closed' ? 'ok' : 'warning'}"></span>
                    <span>Внутренняя шторка: ${stateLabels[status.shutters?.inner] || status.shutters?.inner}</span>
                </div>
            `;
        }
        
        // RFID readers
        const rfid = document.getElementById('rfid-status');
        if (rfid) {
            rfid.innerHTML = `
                <div class="status-item-diag">
                    <span class="status-dot ${status.rfid?.card ? 'ok' : 'error'}"></span>
                    <span>ACR1281U-C (карты): ${status.rfid?.card ? 'Подключен' : 'Нет связи'}</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ${status.rfid?.book ? 'ok' : 'error'}"></span>
                    <span>IQRFID-5102 (книги): ${status.rfid?.book ? 'Подключен' : 'Нет связи'}</span>
                </div>
            `;
        }
        
        // Connections
        const connections = document.getElementById('connections-status');
        if (connections) {
            connections.innerHTML = `
                <div class="status-item-diag">
                    <span class="status-dot ${status.irbisConnected ? 'ok' : 'warning'}"></span>
                    <span>ИРБИС64: ${status.irbisConnected ? 'Подключено' : 'Mock режим'}</span>
                </div>
                <div class="status-item-diag">
                    <span class="status-dot ${ws && ws.readyState === 1 ? 'ok' : 'error'}"></span>
                    <span>WebSocket: ${ws && ws.readyState === 1 ? 'Подключено' : 'Отключено'}</span>
                </div>
            `;
        }
    }
    
    // Load system logs
    loadSystemLogs();
}

async function loadSystemLogs() {
    const result = await api('GET', '/api/logs?limit=50');
    const container = document.getElementById('system-logs');
    if (!container || !result) return;
    
    container.innerHTML = result.map(log => `
        <div class="log-entry ${log.level.toLowerCase()}">${log.timestamp} [${log.level}] ${log.message}</div>
    `).join('');
}

async function testMotor(motor) {
    await api('POST', '/api/test/motor', { motor });
}

async function testLock(lock) {
    await api('POST', '/api/test/lock', { lock });
}

async function testShutter(shutter) {
    await api('POST', '/api/test/shutter', { shutter });
}

async function testRfid(type) {
    await api('POST', '/api/test/rfid', { type });
}

// Settings
async function loadSettings() {
    const result = await api('GET', '/api/settings');
    if (result) {
        document.getElementById('setting-move-timeout').value = result.timeouts?.move || 1500;
        document.getElementById('setting-tray-extend').value = result.timeouts?.tray_extend || 800;
        document.getElementById('setting-user-wait').value = result.timeouts?.user_wait || 30000;
        
        document.getElementById('setting-telegram-enabled').checked = result.telegram?.enabled || false;
        document.getElementById('setting-telegram-token').value = result.telegram?.bot_token || '';
        document.getElementById('setting-telegram-chat').value = result.telegram?.chat_id || '';
        
        document.getElementById('setting-backup-enabled').checked = result.backup?.enabled !== false;
        document.getElementById('setting-backup-interval').value = result.backup?.interval || 24;
        
        document.getElementById('setting-irbis-host').value = result.irbis?.host || '192.168.1.100';
        document.getElementById('setting-irbis-port').value = result.irbis?.port || 6666;
        document.getElementById('setting-irbis-mock').checked = result.irbis?.mock !== false;
    }
}

async function saveSettings() {
    const settings = {
        timeouts: {
            move: parseInt(document.getElementById('setting-move-timeout').value),
            tray_extend: parseInt(document.getElementById('setting-tray-extend').value),
            user_wait: parseInt(document.getElementById('setting-user-wait').value),
        },
        telegram: {
            enabled: document.getElementById('setting-telegram-enabled').checked,
            bot_token: document.getElementById('setting-telegram-token').value,
            chat_id: document.getElementById('setting-telegram-chat').value,
        },
        backup: {
            enabled: document.getElementById('setting-backup-enabled').checked,
            interval: parseInt(document.getElementById('setting-backup-interval').value),
        },
        irbis: {
            host: document.getElementById('setting-irbis-host').value,
            port: parseInt(document.getElementById('setting-irbis-port').value),
            mock: document.getElementById('setting-irbis-mock').checked,
        }
    };
    
    const result = await api('POST', '/api/settings', settings);
    if (result.success) {
        alert('Настройки сохранены');
    } else {
        alert('Ошибка сохранения');
    }
}

async function testTelegram() {
    const result = await api('POST', '/api/test/telegram', {});
    alert(result.success ? 'Сообщение отправлено' : 'Ошибка отправки');
}

async function createBackup() {
    const result = await api('POST', '/api/backup/create', {});
    alert(result.success ? `Бэкап создан: ${result.path}` : 'Ошибка');
}

async function showBackups() {
    const result = await api('GET', '/api/backup/list');
    if (result && result.backups) {
        alert('Бэкапы:\n' + result.backups.join('\n'));
    }
}

async function testIrbis() {
    const result = await api('POST', '/api/test/irbis', {});
    alert(result.success ? 'ИРБИС подключен' : 'Нет связи с ИРБИС');
}

// Navigation
function showScreen(screenId) {
    previousScreen = currentScreen;
    
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
    
    currentScreen = screenId;
    
    // Load data for specific screens
    switch (screenId) {
        case 'book-list':
            updateBooksList();
            break;
        case 'cells-view':
            loadCells();
            break;
        case 'operations-log':
            loadOperations();
            break;
        case 'calibration':
            loadCalibration();
            break;
        case 'diagnostics':
            runDiagnostics();
            break;
        case 'settings':
            loadSettings();
            break;
        case 'extract-books':
            loadExtractionList();
            break;
    }
}

async function loadExtractionList() {
    const result = await api('GET', '/api/cells/extraction');
    const list = document.getElementById('extraction-list');
    if (!list) return;
    
    if (!result || result.length === 0) {
        list.innerHTML = '<p class="center-content">Нет книг для изъятия</p>';
        return;
    }
    
    list.innerHTML = result.map(cell => `
        <div class="list-item">
            <div>
                <h4>${cell.book_title || 'Книга'}</h4>
                <p>Ячейка: ${cell.row} ${cell.x}-${cell.y}</p>
            </div>
            <button class="btn btn-primary" onclick="extractCell(${cell.id})">📦 Изъять</button>
        </div>
    `).join('');
}

function goBack() {
    if (!currentUser) {
        showScreen('welcome-screen');
        return;
    }
    
    switch (currentUser.role) {
        case 'admin':
            showScreen('admin-menu');
            break;
        case 'librarian':
            showScreen('librarian-menu');
            break;
        default:
            showScreen('reader-menu');
    }
}

// Progress & Messages
function setProgress(value, message) {
    document.getElementById('progress-fill').style.width = `${value}%`;
    document.getElementById('progress-message').textContent = message;
}

function updateProgress(data) {
    const percent = (data.step / data.total) * 100;
    setProgress(percent, data.message);
    document.getElementById('progress-step').textContent = `Шаг ${data.step} из ${data.total}`;
}

function updateSensorsDisplay(data) {
    // Update sensors in diagnostics if visible
    if (currentScreen === 'diagnostics') {
        runDiagnostics();
    }
}

function updatePositionDisplay(data) {
    // Position updates for diagnostics
}

function showSuccess(message) {
    document.getElementById('success-message').textContent = message;
    showScreen('success-screen');
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    showScreen('error-screen');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

// ============ HOMING ============
async function runHomingXY() {
    showScreen('progress-screen');
    setProgress(30, 'Хоминг XY по концевикам...');
    const result = await api('POST', '/api/homing/xy', {});
    if (result.success) {
        setProgress(100, 'Хоминг завершён');
        setTimeout(() => { showSuccessScreen('XY захомирован. Позиция: X=0, Y=0'); }, 500);
    } else {
        showErrorScreen(result.error || 'Ошибка хоминга');
    }
}

async function runHomingTray() {
    const result = await api('POST', '/api/homing/tray', {});
    if (result.success) {
        alert('✅ Хоминг лотка завершён');
    } else {
        alert('❌ ' + (result.error || 'Ошибка. Убедитесь что каретка в позиции X=0, Y=0'));
    }
}

async function runAutoCalibration() {
    if (!confirm('Авто-калибровка: каретка объедет все концевики. Убедитесь что шкаф свободен. Продолжить?')) return;
    showScreen('progress-screen');
    setProgress(10, 'Запуск авто-калибровки...');
    const result = await api('POST', '/api/calibration/auto', {});
    if (result.success) {
        const r = result.results;
        showSuccessScreen(`Калибровка завершена!\nmax_x=${r.max_x}, max_y=${r.max_y}\nX: [${r.positions_x.join(', ')}]`);
    } else {
        showErrorScreen(result.error || 'Ошибка авто-калибровки');
    }
}

// ============ TEACH MODE ============
let teachActive = false;
let teachPending = false;

async function teachStart() {
    const name = document.getElementById('teach-name').value.trim();
    if (!name) { alert('Введите название'); return; }
    const result = await api('POST', '/api/teach/start', { name });
    if (result.success) {
        teachActive = true;
        teachPending = false;
        teachLog(result.message);
        updateTeachUI();
    }
}

async function teachExecute(action, params) {
    if (!teachActive) { alert('Сначала начни запись'); return; }
    const result = await api('POST', '/api/teach/execute', { action, params });
    teachLog(result.message);
    teachPending = true;
    updateTeachUI();
}

async function teachExecuteXY() {
    const x = parseInt(prompt('X (шаги):', '0'));
    const y = parseInt(prompt('Y (шаги):', '0'));
    if (isNaN(x) || isNaN(y)) return;
    await teachExecute('move_xy', { x, y });
}

async function teachJog(axis, direction) {
    const steps = parseInt(document.getElementById('jog-steps').value || 100) * direction;
    const result = await api('POST', '/api/teach/jog', { axis, steps });
    teachLog(result.message);
}

async function teachConfirm() {
    const result = await api('POST', '/api/teach/confirm', {});
    teachLog(result.message);
    teachPending = false;
    updateTeachUI();
}

async function teachSkip() {
    const result = await api('POST', '/api/teach/skip', {});
    teachLog(result.message);
    teachPending = false;
    updateTeachUI();
}

async function teachUndo() {
    const result = await api('POST', '/api/teach/undo', {});
    teachLog(result.message);
}

async function teachSave() {
    const result = await api('POST', '/api/teach/save', {});
    teachLog(result.message);
    teachActive = false;
    teachPending = false;
    updateTeachUI();
    loadTeachSequences();
}

async function teachDiscard() {
    if (!confirm('Отменить запись?')) return;
    const result = await api('POST', '/api/teach/discard', {});
    teachLog(result.message);
    teachActive = false;
    teachPending = false;
    updateTeachUI();
}

async function loadTeachSequences() {
    const result = await api('GET', '/api/teach/sequences');
    const el = document.getElementById('teach-sequences-list');
    if (el) el.textContent = result.sequences || 'Нет последовательностей';
}

async function teachPlay(name) {
    if (!confirm(`Воспроизвести "${name}"?`)) return;
    showScreen('progress-screen');
    const result = await api('POST', '/api/teach/play', { name });
    if (result.success) showSuccessScreen(result.message);
    else showErrorScreen(result.message);
}

function teachLog(msg) {
    const el = document.getElementById('teach-log');
    if (!el) return;
    const line = document.createElement('div');
    line.textContent = new Date().toLocaleTimeString() + ' ' + msg;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
}

function updateTeachUI() {
    const badge = document.getElementById('teach-status-badge');
    if (badge) badge.textContent = teachActive ? '🔴 Запись' : '⏹ Не активен';

    const cmds = document.getElementById('teach-commands');
    const jog = document.getElementById('teach-jog');
    if (cmds) cmds.style.opacity = teachActive ? '1' : '0.4';
    if (jog) jog.style.opacity = teachActive ? '1' : '0.4';

    const btnSave = document.getElementById('btn-teach-save');
    const btnDiscard = document.getElementById('btn-teach-discard');
    const btnConfirm = document.getElementById('btn-teach-confirm');
    const btnSkip = document.getElementById('btn-teach-skip');
    if (btnSave) btnSave.disabled = !teachActive;
    if (btnDiscard) btnDiscard.disabled = !teachActive;
    if (btnConfirm) btnConfirm.disabled = !teachPending;
    if (btnSkip) btnSkip.disabled = !teachPending;
}
