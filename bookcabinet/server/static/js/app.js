// State
let currentUser = null;
let currentScreen = 'welcome-screen';
let previousScreen = null;
let reservedBooks = [];
let ws = null;

// WebSocket
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);
    
    ws.onopen = () => console.log('WebSocket connected');
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
            showError(msg.data.message || msg.message);
            break;
        case 'card_read':
            authenticate(msg.data.uid);
            break;
        case 'book_read':
            // Handle book detection
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
    
    const response = await fetch(endpoint, options);
    return response.json();
}

// Authentication
async function authenticate(rfid) {
    showScreen('progress-screen');
    setProgress(50, 'Авторизация...');
    
    try {
        const result = await api('POST', '/api/auth/card', { rfid });
        
        if (result.success) {
            currentUser = result.user;
            reservedBooks = result.reservedBooks || [];
            
            updateUserInfo();
            
            switch (currentUser.role) {
                case 'admin':
                case 'librarian':
                    showScreen('librarian-menu');
                    updateExtractionAlert(result.needsExtraction);
                    break;
                default:
                    showScreen('reader-menu');
            }
        } else {
            showError(result.error || 'Ошибка авторизации');
        }
    } catch (e) {
        showError('Ошибка соединения');
    }
}

function logout() {
    currentUser = null;
    reservedBooks = [];
    showScreen('welcome-screen');
}

// UI Updates
function updateUserInfo() {
    const role = currentUser.role === 'admin' ? 'Админ' : 
                 currentUser.role === 'librarian' ? 'Библиотекарь' : 'Читатель';
    const info = `${currentUser.name} (${role})`;
    
    document.getElementById('user-info').textContent = info;
    document.getElementById('librarian-info').textContent = info;
    document.getElementById('reserved-count').textContent = 
        `${reservedBooks.length} забронировано`;
}

function updateExtractionAlert(count) {
    const alert = document.getElementById('extraction-alert');
    if (count > 0) {
        document.getElementById('extraction-count').textContent = count;
        alert.classList.remove('hidden');
    } else {
        alert.classList.add('hidden');
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
        <div class="list-item">
            <div>
                <h4>${book.title}</h4>
                <p>${book.author || 'Автор неизвестен'}</p>
            </div>
            <button class="btn btn-primary" onclick="issueBook('${book.rfid}')">
                📖 Забрать
            </button>
        </div>
    `).join('');
}

// Operations
async function issueBook(bookRfid) {
    showScreen('progress-screen');
    setProgress(20, `Выдача книги...`);
    
    try {
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
    } catch (e) {
        showError('Ошибка операции');
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
    
    try {
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
    } catch (e) {
        showError('Ошибка загрузки');
    }
}

async function extractAll() {
    showScreen('progress-screen');
    setProgress(20, 'Изъятие всех книг...');
    
    try {
        const result = await api('POST', '/api/extract-all', {});
        
        if (result.success) {
            showSuccess(`Изъято ${result.extracted} книг`);
        } else {
            showError(result.error || 'Ошибка изъятия');
        }
    } catch (e) {
        showError('Ошибка операции');
    }
}

async function runInventory() {
    showScreen('progress-screen');
    setProgress(10, 'Инвентаризация...');
    
    try {
        const result = await api('POST', '/api/run-inventory', {});
        showSuccess(`Найдено ${result.found} книг, отсутствует ${result.missing}`);
    } catch (e) {
        showError('Ошибка инвентаризации');
    }
}

// Navigation
function showScreen(screenId) {
    previousScreen = currentScreen;
    
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
    
    currentScreen = screenId;
    
    if (screenId === 'book-list') {
        updateBooksList();
    }
}

function goBack() {
    if (!currentUser) {
        showScreen('welcome-screen');
        return;
    }
    
    switch (currentUser.role) {
        case 'admin':
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
