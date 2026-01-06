"""
ИРБИС64 интеграция

Модули:
- client: Полноценный TCP клиент для ИРБИС64
- mock: Mock реализация для тестирования
- service: Унифицированный сервис библиотечных операций
"""
from .client import IrbisClient, IrbisConfig
from .mock import MockIrbis, mock_irbis
from .service import LibraryService, library_service

__all__ = [
    'IrbisClient',
    'IrbisConfig', 
    'MockIrbis',
    'mock_irbis',
    'LibraryService',
    'library_service',
]
