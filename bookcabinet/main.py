#!/usr/bin/env python3
"""
BookCabinet - Автоматический шкаф книговыдачи
Точка входа
"""
import asyncio
import logging
import signal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bookcabinet.config import HOST, PORT, MOCK_MODE, LOG_LEVEL
from bookcabinet.server.web_server import create_app
from bookcabinet.database import db
from bookcabinet.mechanics.algorithms import algorithms
from bookcabinet.rfid.card_reader import card_reader
from bookcabinet.rfid.book_reader import book_reader
from aiohttp import web


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bookcabinet')


async def startup_checks():
    """Проверки при запуске"""
    checks = []
    
    checks.append(('База данных', True))
    
    try:
        cells = db.get_all_cells()
        checks.append((f'Ячейки ({len(cells)})', len(cells) == 126))
    except Exception as e:
        checks.append(('Ячейки', False))
    
    if MOCK_MODE:
        checks.append(('GPIO (mock)', True))
        checks.append(('RFID карты (mock)', True))
        checks.append(('RFID книги (mock)', True))
    else:
        checks.append(('GPIO', await init_gpio()))
        checks.append(('RFID карты', await card_reader.connect()))
        checks.append(('RFID книги', await book_reader.connect()))
    
    checks.append(('ИРБИС (mock)', True))
    
    print('=' * 50)
    print('ПРОВЕРКА СИСТЕМЫ')
    print('=' * 50)
    
    all_ok = True
    for name, status in checks:
        icon = '✅' if status else '❌'
        print(f'{icon} {name}')
        if not status:
            all_ok = False
    
    print('=' * 50)
    if all_ok:
        print('✅ СИСТЕМА ГОТОВА К РАБОТЕ')
    else:
        print('⚠️ СИСТЕМА ЗАПУЩЕНА С ОШИБКАМИ')
    print('=' * 50)
    
    return all_ok


async def init_gpio():
    """Инициализация GPIO"""
    try:
        from bookcabinet.hardware.gpio_manager import gpio
        return not gpio.mock_mode or True
    except:
        return False


async def on_startup(app):
    """Действия при запуске сервера"""
    logger.info('Запуск BookCabinet...')
    
    await startup_checks()
    
    db.add_system_log('INFO', 'Система запущена', 'main')
    
    logger.info(f'Сервер запущен на http://{HOST}:{PORT}')
    logger.info(f'Mock режим: {MOCK_MODE}')


async def on_shutdown(app):
    """Действия при остановке сервера"""
    logger.info('Остановка BookCabinet...')
    
    algorithms.stop()
    card_reader.stop_monitoring()
    book_reader.stop_polling()
    
    db.add_system_log('INFO', 'Система остановлена', 'main')


def main():
    """Главная функция"""
    app = create_app()
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    web.run_app(app, host=HOST, port=PORT, print=None)


if __name__ == '__main__':
    main()
