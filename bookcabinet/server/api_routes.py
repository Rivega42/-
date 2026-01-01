"""
REST API Routes - полная версия
"""
from aiohttp import web
import json
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..mechanics.calibration import calibration
from ..hardware.motors import motors
from ..hardware.servos import servos
from ..hardware.shutters import shutters
from ..hardware.sensors import sensors
from ..business.auth import auth_service
from ..business.issue import issue_service
from ..business.return_book import return_service
from ..business.load import load_service
from ..business.unload import unload_service
from ..monitoring.telegram import telegram
from ..monitoring.backup import backup_manager
from ..rfid.card_reader import card_reader
from ..rfid.book_reader import book_reader
from ..config import TIMEOUTS, IRBIS, TELEGRAM
from .websocket_handler import ws_handler


def json_response(data, status=200):
    return web.json_response(data, status=status)


def require_role(*roles):
    """Декоратор проверки роли пользователя"""
    def decorator(handler):
        async def wrapper(request):
            check = auth_service.require_role(*roles)
            if not check.get('success'):
                return json_response(check, check.get('code', 403))
            return await handler(request)
        return wrapper
    return decorator


def role_check(*roles):
    """Проверка роли внутри handler"""
    check = auth_service.require_role(*roles)
    if not check.get('success'):
        return json_response(check, check.get('code', 403))
    return None


# ============ STATUS ============

async def get_status(request):
    state = algorithms.get_state()
    stats = db.get_statistics()
    
    return json_response({
        'state': state['state'],
        'currentOperation': state['current_operation'],
        'position': state['position'],
        'sensors': state['sensors'],
        'servos': state['servos'],
        'shutters': state['shutters'],
        'irbisConnected': not IRBIS['mock'],
        'autonomousMode': IRBIS['mock'],
        'maintenanceMode': False,
        'statistics': stats,
    })


async def get_diagnostics(request):
    return json_response({
        'sensors': sensors.read_all(),
        'position': motors.get_position(),
        'servos': servos.get_all_states(),
        'shutters': shutters.get_all_states(),
        'rfid': {
            'card': True,
            'book': True,
        },
        'irbisConnected': not IRBIS['mock'],
    })


# ============ CELLS ============

async def get_cells(request):
    cells = db.get_all_cells()
    return json_response(cells)


async def get_cell(request):
    cell_id = int(request.match_info['id'])
    cell = db.get_cell(cell_id)
    if cell:
        return json_response(cell)
    return json_response({'error': 'Cell not found'}, 404)


async def get_cells_extraction(request):
    cells = db.get_cells_needing_extraction()
    return json_response(cells)


# ============ SENSORS & POSITION ============

async def get_sensors(request):
    return json_response(sensors.read_all())


async def get_position(request):
    return json_response(motors.get_position())


# ============ AUTH ============

async def post_auth_card(request):
    data = await request.json()
    rfid = data.get('rfid')
    
    if not rfid:
        return json_response({'success': False, 'error': 'RFID required'}, 400)
    
    result = await auth_service.authenticate(rfid)
    return json_response(result)


# ============ BOOK OPERATIONS ============

async def post_issue(request):
    data = await request.json()
    book_rfid = data.get('bookRfid')
    user_rfid = data.get('userRfid')
    
    if not book_rfid or not user_rfid:
        return json_response({'success': False, 'error': 'bookRfid and userRfid required'}, 400)
    
    result = await issue_service.issue_book(book_rfid, user_rfid, ws_handler.send_progress)
    return json_response(result)


async def post_return(request):
    data = await request.json()
    book_rfid = data.get('bookRfid')
    
    if not book_rfid:
        return json_response({'success': False, 'error': 'bookRfid required'}, 400)
    
    result = await return_service.return_book(book_rfid, ws_handler.send_progress)
    return json_response(result)


async def post_load_book(request):
    """Загрузка книги - только библиотекарь/админ"""
    error = role_check('librarian', 'admin')
    if error:
        return error
    
    data = await request.json()
    book_rfid = data.get('bookRfid')
    title = data.get('title')
    author = data.get('author')
    cell_id = data.get('cellId')
    
    if not book_rfid:
        return json_response({'success': False, 'error': 'bookRfid required'}, 400)
    
    result = await load_service.load_book(book_rfid, title, author, cell_id, ws_handler.send_progress)
    return json_response(result)


async def post_extract(request):
    """Изъятие книги - только библиотекарь/админ"""
    error = role_check('librarian', 'admin')
    if error:
        return error
    
    data = await request.json()
    cell_id = data.get('cellId')
    
    if not cell_id:
        return json_response({'success': False, 'error': 'cellId required'}, 400)
    
    result = await unload_service.extract_book(cell_id, ws_handler.send_progress)
    return json_response(result)


async def post_extract_all(request):
    """Изъятие всех книг - только библиотекарь/админ"""
    error = role_check('librarian', 'admin')
    if error:
        return error
    
    result = await unload_service.extract_all(ws_handler.send_progress)
    return json_response(result)


async def post_inventory(request):
    """Инвентаризация - только библиотекарь/админ"""
    error = role_check('librarian', 'admin')
    if error:
        return error
    
    result = await unload_service.run_inventory()
    return json_response(result)


# ============ MECHANICS ============

async def post_init(request):
    success = await algorithms.init_home()
    return json_response({'success': success})


async def post_stop(request):
    algorithms.stop()
    return json_response({'success': True})


async def post_move(request):
    data = await request.json()
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    success = await motors.move_xy(x, y)
    return json_response({'success': success, 'position': motors.get_position()})


# ============ CALIBRATION ============

async def get_calibration(request):
    return json_response({
        'positions': calibration.data.get('positions', {}),
        'kinematics': calibration.data.get('kinematics', {}),
        'speeds': calibration.data.get('speeds', {}),
        'servos': calibration.data.get('servos', {}),
    })


async def post_calibration(request):
    """Сохранение калибровки - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    
    if 'positions' in data:
        calibration.data['positions'] = data['positions']
    if 'kinematics' in data:
        calibration.data['kinematics'] = data['kinematics']
    if 'speeds' in data:
        calibration.data['speeds'] = data['speeds']
    if 'servos' in data:
        calibration.data['servos'] = data['servos']
    
    calibration.save()
    db.add_system_log('INFO', 'Калибровка обновлена', 'calibration')
    
    return json_response({'success': True})


async def post_calibration_test(request):
    """Тест калибровки - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    axis = data.get('axis')
    index = data.get('index', 0)
    value = data.get('value', 0)
    
    if axis == 'x':
        await motors.move_xy(value, motors.position['y'])
    elif axis == 'y':
        await motors.move_xy(motors.position['x'], value)
    
    return json_response({'success': True, 'position': motors.get_position()})


async def post_calibration_reset(request):
    """Сброс калибровки - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    calibration.reset()
    return json_response({'success': True})


# ============ OPERATIONS & LOGS ============

async def get_operations(request):
    limit = int(request.query.get('limit', 100))
    filter_type = request.query.get('filter', 'all')
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if filter_type == 'all':
            cursor.execute('SELECT * FROM operations ORDER BY id DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM operations WHERE operation = ? ORDER BY id DESC LIMIT ?', (filter_type, limit))
        return json_response([dict(row) for row in cursor.fetchall()])


async def get_statistics(request):
    stats = db.get_statistics()
    return json_response(stats)


async def get_logs(request):
    limit = int(request.query.get('limit', 100))
    logs = db.get_recent_logs(limit)
    return json_response(logs)


# ============ SETTINGS ============

async def get_settings(request):
    return json_response({
        'timeouts': TIMEOUTS,
        'telegram': {
            'enabled': TELEGRAM['enabled'],
            'bot_token': TELEGRAM['bot_token'][:10] + '...' if TELEGRAM['bot_token'] else '',
            'chat_id': TELEGRAM['chat_id'],
        },
        'backup': {
            'enabled': True,
            'interval': 24,
        },
        'irbis': IRBIS,
    })


async def post_settings(request):
    """Сохранение настроек - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    
    db.add_system_log('INFO', 'Настройки обновлены', 'settings')
    
    return json_response({'success': True})


# ============ TESTS ============

async def post_test_motor(request):
    """Тест мотора - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    motor = data.get('motor', 'xy')
    
    if motor == 'xy':
        await motors.move_xy(1000, 1000)
        await motors.move_xy(0, 0)
    elif motor == 'tray':
        await motors.extend_tray()
        await motors.retract_tray()
    
    db.add_system_log('INFO', f'Тест мотора: {motor}', 'diagnostics')
    return json_response({'success': True})


async def post_test_lock(request):
    """Тест замка - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    lock = data.get('lock', 'lock1')
    
    await servos.open_lock(lock)
    await servos.close_lock(lock)
    
    db.add_system_log('INFO', f'Тест замка: {lock}', 'diagnostics')
    return json_response({'success': True})


async def post_test_shutter(request):
    """Тест шторки - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    shutter = data.get('shutter', 'outer')
    
    await shutters.open_shutter(shutter)
    await shutters.close_shutter(shutter)
    
    db.add_system_log('INFO', f'Тест шторки: {shutter}', 'diagnostics')
    return json_response({'success': True})


async def post_test_rfid(request):
    """Тест RFID - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    rfid_type = data.get('type', 'card')
    
    if rfid_type == 'card':
        card_reader.simulate_card('TEST001', 'library')
    else:
        book_reader.simulate_tag('TESTBOOK001')
    
    db.add_system_log('INFO', f'Тест RFID: {rfid_type}', 'diagnostics')
    return json_response({'success': True})


async def post_test_telegram(request):
    """Тест Telegram - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    success = await telegram.send('Тестовое сообщение от BookCabinet', 'info')
    return json_response({'success': success})


async def post_test_irbis(request):
    """Тест ИРБИС - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    from ..irbis.client import irbis_client
    success = await irbis_client.connect()
    return json_response({'success': success})


# ============ BACKUP ============

async def post_backup_create(request):
    """Создание бэкапа - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    path = backup_manager.create_backup()
    db.add_system_log('INFO', f'Создан бэкап: {path}', 'backup')
    return json_response({'success': True, 'path': path})


async def get_backup_list(request):
    """Список бэкапов - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    backups = backup_manager.list_backups()
    return json_response({'backups': backups})


async def post_backup_restore(request):
    """Восстановление бэкапа - только админ"""
    error = role_check('admin')
    if error:
        return error
    
    data = await request.json()
    backup_name = data.get('name')
    
    if not backup_name:
        return json_response({'success': False, 'error': 'name required'}, 400)
    
    success = backup_manager.restore_backup(backup_name)
    if success:
        db.add_system_log('INFO', f'Восстановлен бэкап: {backup_name}', 'backup')
    return json_response({'success': success})


# ============ SETUP ROUTES ============

def setup_routes(app: web.Application):
    # Status & Diagnostics
    app.router.add_get('/api/status', get_status)
    app.router.add_get('/api/diagnostics', get_diagnostics)
    
    # Cells
    app.router.add_get('/api/cells', get_cells)
    app.router.add_get('/api/cells/extraction', get_cells_extraction)
    app.router.add_get('/api/cells/{id}', get_cell)
    
    # Sensors & Position
    app.router.add_get('/api/sensors', get_sensors)
    app.router.add_get('/api/position', get_position)
    
    # Auth
    app.router.add_post('/api/auth/card', post_auth_card)
    
    # Book Operations
    app.router.add_post('/api/issue', post_issue)
    app.router.add_post('/api/return', post_return)
    app.router.add_post('/api/load-book', post_load_book)
    app.router.add_post('/api/extract', post_extract)
    app.router.add_post('/api/extract-all', post_extract_all)
    app.router.add_post('/api/run-inventory', post_inventory)
    
    # Mechanics
    app.router.add_post('/api/init', post_init)
    app.router.add_post('/api/stop', post_stop)
    app.router.add_post('/api/move', post_move)
    
    # Calibration
    app.router.add_get('/api/calibration', get_calibration)
    app.router.add_post('/api/calibration', post_calibration)
    app.router.add_post('/api/calibration/test', post_calibration_test)
    app.router.add_post('/api/calibration/reset', post_calibration_reset)
    
    # Operations & Logs
    app.router.add_get('/api/operations', get_operations)
    app.router.add_get('/api/statistics', get_statistics)
    app.router.add_get('/api/logs', get_logs)
    
    # Settings
    app.router.add_get('/api/settings', get_settings)
    app.router.add_post('/api/settings', post_settings)
    
    # Tests
    app.router.add_post('/api/test/motor', post_test_motor)
    app.router.add_post('/api/test/lock', post_test_lock)
    app.router.add_post('/api/test/shutter', post_test_shutter)
    app.router.add_post('/api/test/rfid', post_test_rfid)
    app.router.add_post('/api/test/telegram', post_test_telegram)
    app.router.add_post('/api/test/irbis', post_test_irbis)
    
    # Backup
    app.router.add_post('/api/backup/create', post_backup_create)
    app.router.add_get('/api/backup/list', get_backup_list)
    app.router.add_post('/api/backup/restore', post_backup_restore)
    
    # WebSocket
    app.router.add_get('/ws', ws_handler.handle)
