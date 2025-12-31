"""
REST API Routes
"""
from aiohttp import web
import json

from ..database import db
from ..mechanics.algorithms import algorithms
from ..business.auth import auth_service
from ..business.issue import issue_service
from ..business.return_book import return_service
from ..business.load import load_service
from ..business.unload import unload_service
from .websocket_handler import ws_handler


def json_response(data, status=200):
    return web.json_response(data, status=status)


async def get_status(request):
    state = algorithms.get_state()
    stats = db.get_statistics()
    
    return json_response({
        'state': state['state'],
        'currentOperation': state['current_operation'],
        'position': state['position'],
        'sensors': state['sensors'],
        'maintenanceMode': False,
        'irbisConnected': True,
        'statistics': stats,
    })


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


async def get_sensors(request):
    from ..hardware.sensors import sensors
    return json_response(sensors.read_all())


async def get_position(request):
    from ..hardware.motors import motors
    return json_response(motors.get_position())


async def post_auth_card(request):
    data = await request.json()
    rfid = data.get('rfid')
    
    if not rfid:
        return json_response({'success': False, 'error': 'RFID required'}, 400)
    
    result = await auth_service.authenticate(rfid)
    return json_response(result)


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
    data = await request.json()
    cell_id = data.get('cellId')
    
    if not cell_id:
        return json_response({'success': False, 'error': 'cellId required'}, 400)
    
    result = await unload_service.extract_book(cell_id, ws_handler.send_progress)
    return json_response(result)


async def post_extract_all(request):
    result = await unload_service.extract_all(ws_handler.send_progress)
    return json_response(result)


async def post_inventory(request):
    result = await unload_service.run_inventory()
    return json_response(result)


async def post_init(request):
    success = await algorithms.init_home()
    return json_response({'success': success})


async def post_stop(request):
    algorithms.stop()
    return json_response({'success': True})


async def get_operations(request):
    limit = int(request.query.get('limit', 100))
    return json_response([])


async def get_statistics(request):
    stats = db.get_statistics()
    return json_response(stats)


async def get_logs(request):
    limit = int(request.query.get('limit', 100))
    logs = db.get_recent_logs(limit)
    return json_response(logs)


def setup_routes(app: web.Application):
    app.router.add_get('/api/status', get_status)
    app.router.add_get('/api/cells', get_cells)
    app.router.add_get('/api/cells/{id}', get_cell)
    app.router.add_get('/api/cells/extraction', get_cells_extraction)
    app.router.add_get('/api/sensors', get_sensors)
    app.router.add_get('/api/position', get_position)
    
    app.router.add_post('/api/auth/card', post_auth_card)
    app.router.add_post('/api/issue', post_issue)
    app.router.add_post('/api/return', post_return)
    app.router.add_post('/api/load-book', post_load_book)
    app.router.add_post('/api/extract', post_extract)
    app.router.add_post('/api/extract-all', post_extract_all)
    app.router.add_post('/api/run-inventory', post_inventory)
    
    app.router.add_post('/api/init', post_init)
    app.router.add_post('/api/stop', post_stop)
    
    app.router.add_get('/api/operations', get_operations)
    app.router.add_get('/api/statistics', get_statistics)
    app.router.add_get('/api/logs', get_logs)
    
    app.router.add_get('/ws', ws_handler.handle)
