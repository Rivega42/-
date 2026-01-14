"""
Unified Card Reader - параллельный опрос ACR1281U-C (NFC) и IQRFID-5102 (UHF)

Для идентификации пользователя используются ДВА считывателя одновременно:
- ACR1281U-C (NFC 13.56MHz) → читательский билет библиотеки  
- IQRFID-5102 (UHF 900MHz) → ЕКП (Единая Карта Петербуржца)

Оба сливаются в единый callback on_card_read() с нормализованным UID.

Нормализация UID (по референсу C#):
- Удаление разделителей: : - пробелы
- Приведение к верхнему регистру
- Для UHF: обрезка EPC до 24 символов (UhfCardUidLength)

Использование:
    from rfid.unified_card_reader import unified_reader
    
    def on_card(uid: str, source: str):
        print(f"Карта {uid} от {source}")
    
    unified_reader.on_card_read = on_card
    await unified_reader.start()
"""
import asyncio
import re
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from datetime import datetime
import time

# Импорт существующего драйвера IQRFID-5102
from ..hardware.iqrfid5102_driver import IQRFID5102

# Константы из референса C#
UHF_CARD_UID_LENGTH = 24  # Обрезка EPC для UHF карт
DEBOUNCE_MS = 800  # Защита от дребезга
UID_STRIP_DELIMITERS = True  # Удалять разделители
UID_UPPER_HEX = True  # Верхний регистр


@dataclass
class CardReadEvent:
    """Событие чтения карты"""
    uid: str  # Нормализованный UID
    raw_uid: str  # Исходный UID
    source: str  # 'nfc' или 'uhf'
    timestamp: datetime


def normalize_uid(raw_uid: str, is_uhf: bool = False) -> str:
    """
    Нормализация UID карты (алгоритм из C# референса)
    
    Args:
        raw_uid: Исходный UID
        is_uhf: True если UHF карта (нужна обрезка до 24 символов)
    
    Returns:
        Нормализованный UID
    """
    if not raw_uid:
        return ""
    
    uid = raw_uid
    
    # Удаление разделителей: : - пробелы
    if UID_STRIP_DELIMITERS:
        uid = re.sub(r'[:\-\s]', '', uid)
    
    # Верхний регистр
    if UID_UPPER_HEX:
        uid = uid.upper()
    
    # Для UHF карт обрезаем EPC до 24 символов
    if is_uhf and len(uid) > UHF_CARD_UID_LENGTH:
        uid = uid[:UHF_CARD_UID_LENGTH]
    
    return uid


class UnifiedCardReader:
    """
    Унифицированный считыватель карт
    
    Параллельно опрашивает NFC и UHF считыватели,
    нормализует UID и вызывает единый callback.
    """
    
    def __init__(self):
        # Callbacks
        self.on_card_read: Optional[Callable[[str, str], None]] = None
        self.on_card_event: Optional[Callable[[CardReadEvent], None]] = None
        
        self._running = False
        self._last_uid_time: Dict[str, float] = {}  # Для debounce
        
        # NFC reader (ACR1281U-C через PC/SC)
        self._nfc_reader = None
        self._nfc_available = False
        
        # UHF reader (IQRFID-5102) - используем существующий драйвер
        self._uhf_reader: Optional[IQRFID5102] = None
        self._uhf_available = False
        self._uhf_port = '/dev/ttyUSB0'
        
        # Mock режим
        self.mock_mode = False
    
    def configure(self, 
                  uhf_port: str = '/dev/ttyUSB0',
                  mock_mode: bool = False):
        """Конфигурация считывателей"""
        self._uhf_port = uhf_port
        self.mock_mode = mock_mode
    
    async def connect(self) -> Dict[str, bool]:
        """
        Подключение к обоим считывателям
        
        Returns:
            {'nfc': bool, 'uhf': bool} - статус подключения
        """
        results = {'nfc': False, 'uhf': False}
        
        if self.mock_mode:
            self._nfc_available = True
            self._uhf_available = True
            print("[UnifiedReader] Mock режим активен")
            return {'nfc': True, 'uhf': True}
        
        # Сначала отключаемся, если уже были подключены
        self._disconnect_readers()
        
        # Подключение NFC (PC/SC)
        results['nfc'] = await self._connect_nfc()
        
        # Подключение UHF (используем существующий драйвер)
        results['uhf'] = self._connect_uhf()
        
        return results
    
    async def _connect_nfc(self) -> bool:
        """Подключение к ACR1281U-C через PC/SC"""
        try:
            from smartcard.System import readers
            
            available = readers()
            if not available:
                print("[NFC] Считыватели не найдены")
                return False
            
            # Ищем ACR1281
            for r in available:
                reader_name = str(r)
                if 'ACR' in reader_name or 'ACS' in reader_name:
                    self._nfc_reader = r
                    self._nfc_available = True
                    print(f"[NFC] Подключен: {reader_name}")
                    return True
            
            # Берём первый доступный
            self._nfc_reader = available[0]
            self._nfc_available = True
            print(f"[NFC] Подключен (fallback): {self._nfc_reader}")
            return True
            
        except ImportError:
            print("[NFC] pyscard не установлен, NFC недоступен")
            return False
        except Exception as e:
            print(f"[NFC] Ошибка подключения: {e}")
            return False
    
    def _connect_uhf(self) -> bool:
        """Подключение к IQRFID-5102 через существующий драйвер"""
        try:
            # Проверяем fallback порт если основной не доступен
            import os
            uhf_port = self._uhf_port
            if not os.path.exists(uhf_port):
                # Пробуем fallback
                if uhf_port == '/dev/rfid_uhf_card':
                    fallback = '/dev/ttyUSB0'
                    if os.path.exists(fallback):
                        print(f"[UHF] Используем fallback порт: {fallback}")
                        uhf_port = fallback
            
            self._uhf_reader = IQRFID5102(uhf_port, debug=False)
            
            if self._uhf_reader.connect():
                self._uhf_available = True
                print(f"[UHF] Подключен: {uhf_port}")
                return True
            else:
                print(f"[UHF] Не удалось подключиться к {uhf_port}")
                return False
                
        except Exception as e:
            print(f"[UHF] Ошибка подключения: {e}")
            return False
    
    def _disconnect_readers(self):
        """Отключение только объектов считывателей, без сброса флагов доступности"""
        if self._uhf_reader:
            try:
                self._uhf_reader.disconnect()
            except:
                pass
            self._uhf_reader = None
        
        self._nfc_reader = None
    
    def disconnect(self):
        """Полное отключение от считывателей"""
        self._running = False
        
        self._disconnect_readers()
        
        # Сбрасываем флаги доступности
        self._nfc_available = False
        self._uhf_available = False
        print("[UnifiedReader] Отключен")
    
    async def start(self, poll_interval: float = 0.3):
        """
        Запуск параллельного опроса обоих считывателей
        
        Args:
            poll_interval: Интервал опроса в секундах
        """
        self._running = True
        self._last_uid_time.clear()
        
        print("[UnifiedReader] Запуск параллельного опроса NFC + UHF")
        
        # Запускаем оба цикла параллельно
        tasks = []
        
        if self._nfc_available:
            tasks.append(asyncio.create_task(self._poll_nfc_loop(poll_interval)))
        
        if self._uhf_available:
            tasks.append(asyncio.create_task(self._poll_uhf_loop(poll_interval)))
        
        if not tasks:
            print("[UnifiedReader] Нет доступных считывателей!")
            return
        
        # Ждём завершения (или stop())
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
    
    def stop(self):
        """Остановка опроса"""
        self._running = False
        print("[UnifiedReader] Остановка опроса")
    
    async def _poll_nfc_loop(self, interval: float):
        """Цикл опроса NFC считывателя"""
        print("[NFC] Цикл опроса запущен")
        
        while self._running:
            try:
                uid = self._read_nfc_card()
                if uid:
                    self._handle_card(uid, 'nfc')
            except Exception as e:
                if self._running:
                    # Ошибка чтения - карта убрана или проблема связи
                    pass
            
            await asyncio.sleep(interval)
        
        print("[NFC] Цикл опроса остановлен")
    
    async def _poll_uhf_loop(self, interval: float):
        """Цикл опроса UHF считывателя"""
        print("[UHF] Цикл опроса запущен")
        
        while self._running:
            try:
                # Используем inventory() из драйвера
                tags = self._uhf_reader.inventory(rounds=1)
                
                for epc in tags:
                    self._handle_card(epc, 'uhf')
                    
            except Exception as e:
                if self._running:
                    print(f"[UHF] Ошибка чтения: {e}")
            
            await asyncio.sleep(interval)
        
        print("[UHF] Цикл опроса остановлен")
    
    def _read_nfc_card(self) -> Optional[str]:
        """Чтение карты с NFC считывателя"""
        if not self._nfc_reader:
            return None
        
        try:
            connection = self._nfc_reader.createConnection()
            connection.connect()
            
            # GET UID command (APDU)
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(GET_UID)
            
            connection.disconnect()
            
            if sw1 == 0x90 and sw2 == 0x00 and data:
                uid = ''.join(format(x, '02X') for x in data)
                return uid
                
        except Exception:
            # Нет карты или ошибка - это нормально
            pass
        
        return None
    
    def _handle_card(self, raw_uid: str, source: str):
        """
        Обработка прочитанной карты с debounce
        
        Args:
            raw_uid: Исходный UID/EPC
            source: 'nfc' или 'uhf'
        """
        # Нормализация UID
        is_uhf = (source == 'uhf')
        uid = normalize_uid(raw_uid, is_uhf=is_uhf)
        
        if not uid:
            return
        
        # Debounce - проверяем не было ли этой карты недавно
        now = time.time()
        last_time = self._last_uid_time.get(uid, 0)
        
        if (now - last_time) * 1000 < DEBOUNCE_MS:
            return  # Слишком рано, пропускаем
        
        self._last_uid_time[uid] = now
        
        # Создаём событие
        event = CardReadEvent(
            uid=uid,
            raw_uid=raw_uid,
            source=source,
            timestamp=datetime.now()
        )
        
        print(f"[{source.upper()}] Карта: {uid}")
        
        # Вызываем callbacks
        if self.on_card_read:
            try:
                self.on_card_read(uid, source)
            except Exception as e:
                print(f"[UnifiedReader] Ошибка в callback: {e}")
        
        if self.on_card_event:
            try:
                self.on_card_event(event)
            except Exception as e:
                print(f"[UnifiedReader] Ошибка в event callback: {e}")
    
    def simulate_card(self, uid: str, source: str = 'nfc'):
        """
        Симуляция чтения карты (для тестов)
        
        Args:
            uid: UID карты
            source: 'nfc' или 'uhf'
        """
        self._handle_card(uid, source)
    
    def get_status(self) -> Dict:
        """
        Получение статуса считывателей
        
        Возвращает dict с ключами для совместимости с API:
        - nfc_connected: bool
        - uhf_connected: bool
        - polling: bool
        - И детальную информацию
        """
        return {
            # Ключи для API routes (get_diagnostics, get_card_readers_status)
            'nfc_connected': self._nfc_available,
            'uhf_connected': self._uhf_available,
            'polling': self._running,
            
            # Дополнительная информация
            'running': self._running,
            'mock_mode': self.mock_mode,
            'nfc': {
                'available': self._nfc_available,
                'reader': str(self._nfc_reader) if self._nfc_reader else None,
            },
            'uhf': {
                'available': self._uhf_available,
                'port': self._uhf_port,
            },
        }


# Синглтон для использования в приложении
unified_reader = UnifiedCardReader()


# ============================================================================
# Тест
# ============================================================================
if __name__ == "__main__":
    import sys
    
    # Для запуска как standalone скрипт - патчим импорт
    class MockIQRFID5102:
        def __init__(self, port, debug=False):
            self.port = port
            self.connected = False
        def connect(self):
            print(f"[MockUHF] Подключение к {self.port}...")
            self.connected = True
            return True
        def disconnect(self):
            self.connected = False
        def inventory(self, rounds=1):
            return []
    
    # Подменяем импорт для теста
    IQRFID5102 = MockIQRFID5102
    
    # Определяем порт UHF
    if sys.platform == 'win32':
        uhf_port = "COM2"
    else:
        uhf_port = "/dev/ttyUSB0"
    
    if len(sys.argv) > 1:
        uhf_port = sys.argv[1]
    
    print("=== Тест UnifiedCardReader ===")
    print(f"UHF порт: {uhf_port}")
    print()
    
    # Callback при чтении карты
    def on_card(uid: str, source: str):
        print(f">>> КАРТА ОБНАРУЖЕНА: {uid} (источник: {source})")
    
    reader = UnifiedCardReader()
    reader.configure(uhf_port=uhf_port)
    reader.on_card_read = on_card
    
    async def main():
        # Подключаемся
        status = await reader.connect()
        print(f"Статус подключения: {status}")
        
        if not status['nfc'] and not status['uhf']:
            print("Нет доступных считывателей!")
            print("Тест симуляции...")
            reader._nfc_available = True
            reader.simulate_card("04AABBCCDD", "nfc")
            reader.simulate_card("E200001122334455667788990011223344", "uhf")
            return
        
        print("\nОжидание карты... (Ctrl+C для выхода)")
        print("Поднеси читательский билет (NFC) или ЕКП (UHF)\n")
        
        try:
            await reader.start(poll_interval=0.3)
        except KeyboardInterrupt:
            print("\nОстановка...")
        finally:
            reader.disconnect()
    
    asyncio.run(main())
