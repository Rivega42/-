"""
Резервное копирование с расписанием и ротацией
"""
import os
import shutil
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..config import DATABASE_PATH
from ..database import db


class BackupManager:
    def __init__(self, backup_dir: str = 'bookcabinet/backups', keep_days: int = 30):
        self.backup_dir = backup_dir
        self.keep_days = keep_days
        self.max_backups = 50
        self.auto_backup_interval = 24 * 60 * 60
        self._running = False
        self._task = None
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, reason: str = 'manual') -> str:
        """Создать резервную копию"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}_{reason}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        try:
            os.makedirs(backup_path, exist_ok=True)
            
            if os.path.exists(DATABASE_PATH):
                shutil.copy2(DATABASE_PATH, os.path.join(backup_path, 'shelf_data.db'))
            
            calibration_path = 'bookcabinet/calibration.json'
            if os.path.exists(calibration_path):
                shutil.copy2(calibration_path, os.path.join(backup_path, 'calibration.json'))
            
            metadata = {
                'created_at': datetime.now().isoformat(),
                'reason': reason,
                'files': os.listdir(backup_path),
            }
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            db.add_system_log('INFO', f'Бэкап создан: {backup_name}', 'backup')
            
            self.cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            db.add_system_log('ERROR', f'Ошибка создания бэкапа: {e}', 'backup')
            return ''
    
    def restore_backup(self, backup_name: str) -> bool:
        """Восстановить из резервной копии"""
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            db.add_system_log('ERROR', f'Бэкап не найден: {backup_name}', 'backup')
            return False
        
        try:
            self.create_backup(reason='pre_restore')
            
            db_backup = os.path.join(backup_path, 'shelf_data.db')
            if os.path.exists(db_backup):
                shutil.copy2(db_backup, DATABASE_PATH)
            
            cal_backup = os.path.join(backup_path, 'calibration.json')
            if os.path.exists(cal_backup):
                shutil.copy2(cal_backup, 'bookcabinet/calibration.json')
            
            db.add_system_log('INFO', f'Восстановлено из бэкапа: {backup_name}', 'backup')
            return True
            
        except Exception as e:
            db.add_system_log('ERROR', f'Ошибка восстановления: {e}', 'backup')
            return False
    
    def list_backups(self) -> List[str]:
        """Получить список резервных копий"""
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        for name in os.listdir(self.backup_dir):
            if name.startswith('backup_'):
                backups.append(name)
        
        return sorted(backups, reverse=True)
    
    def get_backup_info(self, backup_name: str) -> Optional[Dict]:
        """Получить информацию о бэкапе"""
        backup_path = os.path.join(self.backup_dir, backup_name)
        metadata_path = os.path.join(backup_path, 'metadata.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        
        return None
    
    def cleanup_old_backups(self):
        """Удалить старые резервные копии"""
        cutoff = datetime.now() - timedelta(days=self.keep_days)
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            for backup in backups[self.max_backups:]:
                backup_path = os.path.join(self.backup_dir, backup)
                try:
                    shutil.rmtree(backup_path)
                    db.add_system_log('INFO', f'Удалён старый бэкап: {backup}', 'backup')
                except:
                    pass
        
        for name in backups:
            try:
                parts = name.split('_')
                if len(parts) >= 2:
                    timestamp_str = parts[1]
                    backup_date = datetime.strptime(timestamp_str, '%Y%m%d')
                    
                    if backup_date < cutoff:
                        backup_path = os.path.join(self.backup_dir, name)
                        shutil.rmtree(backup_path)
                        db.add_system_log('INFO', f'Удалён устаревший бэкап: {name}', 'backup')
            except:
                pass
    
    async def start_auto_backup(self, interval_hours: int = 24):
        """Запустить автоматическое резервное копирование"""
        self.auto_backup_interval = interval_hours * 60 * 60
        self._running = True
        
        db.add_system_log('INFO', f'Автобэкап запущен (интервал: {interval_hours}ч)', 'backup')
        
        while self._running:
            await asyncio.sleep(self.auto_backup_interval)
            if self._running:
                self.create_backup(reason='auto')
    
    def stop_auto_backup(self):
        """Остановить автоматическое резервное копирование"""
        self._running = False
        db.add_system_log('INFO', 'Автобэкап остановлен', 'backup')
    
    def get_storage_usage(self) -> Dict:
        """Получить информацию об использовании хранилища"""
        total_size = 0
        backup_count = 0
        
        for name in self.list_backups():
            backup_path = os.path.join(self.backup_dir, name)
            if os.path.isdir(backup_path):
                backup_count += 1
                for file in os.listdir(backup_path):
                    file_path = os.path.join(backup_path, file)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
        
        return {
            'backup_count': backup_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
        }


backup_manager = BackupManager()
