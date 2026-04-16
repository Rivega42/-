"""
aiohttp Web Server
"""
import os
from aiohttp import web

from ..config import HOST, PORT
from .api_routes import setup_routes


async def index_handler(request):
    static_dir = os.path.join(os.path.dirname(__file__), 'static'); return web.FileResponse(os.path.join(static_dir, 'index.html'))


def create_app() -> web.Application:
    app = web.Application()
    
    setup_routes(app)
    
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    if os.path.exists(static_path):
        app.router.add_static('/static', static_path)
        app.router.add_static('/assets', os.path.join(static_path, 'assets'))
    
    app.router.add_get('/', index_handler)
    app.router.add_get('/admin', index_handler)
    app.router.add_get('/kiosk', index_handler)
    
    return app


def run_server():
    app = create_app()
    web.run_app(app, host=HOST, port=PORT)
