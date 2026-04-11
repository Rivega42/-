#!/usr/bin/env python3
"""
Bridge: TS server вызывает Python бизнес-логику через subprocess.

Использование из Node.js:
    spawn('python3', ['-m', 'bookcabinet.bridge', 'issue', bookRfid, userRfid])
    spawn('python3', ['-m', 'bookcabinet.bridge', 'return', bookRfid])
    spawn('python3', ['-m', 'bookcabinet.bridge', 'home'])
    spawn('python3', ['-m', 'bookcabinet.bridge', 'stop'])

Вывод: JSON на stdout.
"""
import sys
import json
import asyncio

# Добавляем путь для импорта bookcabinet
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def output(data: dict):
    print(json.dumps(data, ensure_ascii=False), flush=True)


async def cmd_issue(book_rfid: str, user_rfid: str):
    from bookcabinet.business.issue import issue_service

    def on_progress(event):
        output({'type': 'progress', **event})

    result = await issue_service.issue_book(book_rfid, user_rfid, on_progress=on_progress)
    output({'type': 'result', **result})


async def cmd_return(book_rfid: str):
    from bookcabinet.business.return_book import return_service

    def on_progress(event):
        output({'type': 'progress', **event})

    result = await return_service.return_book(book_rfid, on_progress=on_progress)
    output({'type': 'result', **result})


async def cmd_home():
    from bookcabinet.mechanics.algorithms import algorithms
    success = await algorithms.init_home()
    output({'type': 'result', 'success': success})


async def cmd_stop():
    from bookcabinet.mechanics.algorithms import algorithms
    algorithms.stop()
    output({'type': 'result', 'success': True, 'message': 'Emergency stop activated'})


async def cmd_status():
    from bookcabinet.mechanics.algorithms import algorithms
    state = algorithms.get_state()
    output({'type': 'result', 'success': True, **state})


COMMANDS = {
    'issue': lambda args: cmd_issue(args[0], args[1]),
    'return': lambda args: cmd_return(args[0]),
    'home': lambda args: cmd_home(),
    'stop': lambda args: cmd_stop(),
    'status': lambda args: cmd_status(),
}


def main():
    if len(sys.argv) < 2:
        output({'type': 'error', 'message': f'Usage: bridge.py <command> [args...]\nCommands: {", ".join(COMMANDS.keys())}'})
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command not in COMMANDS:
        output({'type': 'error', 'message': f'Unknown command: {command}'})
        sys.exit(1)

    try:
        asyncio.run(COMMANDS[command](args))
    except Exception as e:
        output({'type': 'error', 'message': str(e)})
        sys.exit(1)


if __name__ == '__main__':
    main()
