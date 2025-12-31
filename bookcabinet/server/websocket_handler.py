"""
WebSocket Handler
"""
import json
import asyncio
from typing import Set, Dict, Any
from aiohttp import web, WSMsgType


class WebSocketHandler:
    def __init__(self):
        self.clients: Set[web.WebSocketResponse] = set()
        self._lock = asyncio.Lock()
    
    async def handle(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        async with self._lock:
            self.clients.add(ws)
        
        print(f"WebSocket client connected. Total: {len(self.clients)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(ws, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
        finally:
            async with self._lock:
                self.clients.discard(ws)
            print(f"WebSocket client disconnected. Total: {len(self.clients)}")
        
        return ws
    
    async def _handle_message(self, ws: web.WebSocketResponse, data: str):
        try:
            message = json.loads(data)
            action = message.get('action')
            
            if action == 'ping':
                await ws.send_json({'type': 'pong'})
            
            elif action == 'authenticate':
                from ..business.auth import auth_service
                result = await auth_service.authenticate(message.get('card_rfid', ''))
                await ws.send_json({'type': 'auth_result', 'data': result})
            
            elif action == 'motor':
                pass
            
        except json.JSONDecodeError:
            await ws.send_json({'type': 'error', 'message': 'Invalid JSON'})
        except Exception as e:
            await ws.send_json({'type': 'error', 'message': str(e)})
    
    async def broadcast(self, message: Dict[str, Any]):
        if not self.clients:
            return
        
        data = json.dumps(message)
        async with self._lock:
            dead_clients = set()
            for ws in self.clients:
                try:
                    await ws.send_str(data)
                except:
                    dead_clients.add(ws)
            
            self.clients -= dead_clients
    
    async def send_progress(self, data: Dict[str, Any]):
        await self.broadcast({'type': 'progress', 'data': data})
    
    async def send_error(self, data: Dict[str, Any]):
        await self.broadcast({'type': 'error', 'data': data})
    
    async def send_sensors(self, data: Dict[str, Any]):
        await self.broadcast({'type': 'sensors', 'data': data})
    
    async def send_position(self, x: int, y: int, tray: int):
        await self.broadcast({
            'type': 'position',
            'x': x,
            'y': y,
            'tray': tray
        })


ws_handler = WebSocketHandler()
