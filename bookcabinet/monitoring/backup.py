"""
Резервное копирование
"""
import os
import shutil
from datetime import datetime, timedelta
from typing import List
from ..config import DATABASE_PATH


class BackupManager:
    def __init__(self, backup_dir: str = 'bookcabinet/backups', keep_days: int = 30):
        self.backup_dir = backup_dir
        self.keep_days = keep_days
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)
        
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, os.path.join(backup_path, 'shelf_data.db'))
        
        calibration_path = 'bookcabinet/calibration.json'
        if os.path.exists(calibration_path):
            shutil.copy2(calibration_path, os.path.join(backup_path, 'calibration.json'))
        
        return backup_path
    
    def restore_backup(self, backup_name: str) -> bool:
        backup_path = os.path.join(self.backup_dir, backup_name)
        if not os.path.exists(backup_path):
            return False
        
        db_backup = os.path.join(backup_path, 'shelf_data.db')
        if os.path.exists(db_backup):
            shutil.copy2(db_backup, DATABASE_PATH)
        
        cal_backup = os.path.join(backup_path, 'calibration.json')
        if os.path.exists(cal_backup):
            shutil.copy2(cal_backup, 'bookcabinet/calibration.json')
        
        return True
    
    def list_backups(self) -> List[str]:
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        for name in os.listdir(self.backup_dir):
            if name.startswith('backup_'):
                backups.append(name)
        
        return sorted(backups, reverse=True)
    
    def cleanup_old_backups(self):
        cutoff = datetime.now() - timedelta(days=self.keep_days)
        
        for name in self.list_backups():
            try:
                timestamp_str = name.replace('backup_', '').split('_')[0]
                backup_date = datetime.strptime(timestamp_str, '%Y%m%d')
                
                if backup_date < cutoff:
                    backup_path = os.path.join(self.backup_dir, name)
                    shutil.rmtree(backup_path)
            except:
                pass


backup_manager = BackupManager()
