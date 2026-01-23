# app/storage.py
"""
Storage utilities for managing uploads and temporary files.
Automatically cleans up old files and integrates with R2.
"""
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages temporary file storage and cleanup."""
    
    def __init__(self, base_dir: str, max_age_hours: int = 24):
        """
        Initialize storage manager.
        
        Args:
            base_dir: Base directory for temporary files
            max_age_hours: Maximum age of files before cleanup (default 24 hours)
        """
        self.base_dir = Path(base_dir)
        self.max_age_hours = max_age_hours
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_old_files(self):
        """Remove files older than max_age_hours."""
        try:
            cutoff_time = time.time() - (self.max_age_hours * 3600)
            deleted_count = 0
            freed_space = 0
            
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    # Check file age
                    if file_path.stat().st_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            freed_space += file_size
                            logger.debug(f"Deleted old file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(
                    f"Cleanup: Removed {deleted_count} files, "
                    f"freed {freed_space / 1024 / 1024:.2f} MB"
                )
            
            return deleted_count, freed_space
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0, 0
    
    def get_storage_info(self):
        """Get current storage usage information."""
        total_size = 0
        file_count = 0
        
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size
        
        return {
            "directory": str(self.base_dir),
            "file_count": file_count,
            "total_size_mb": total_size / 1024 / 1024,
            "total_size_gb": total_size / 1024 / 1024 / 1024,
        }


def cleanup_all_temp_directories():
    """Cleanup all temporary directories."""
    backend_dir = Path(__file__).parent.parent
    
    directories = [
        (backend_dir / ".." / "data" / "uploads", 6),  # 6 hours for uploads
        (backend_dir / ".." / "data" / "heatmaps", 24),  # 24 hours for heatmaps
        (backend_dir / ".." / "data" / "reverse-images", 2),  # 2 hours for reverse images
    ]
    
    total_deleted = 0
    total_freed = 0
    
    for directory, max_age in directories:
        if directory.exists():
            manager = StorageManager(str(directory), max_age_hours=max_age)
            deleted, freed = manager.cleanup_old_files()
            total_deleted += deleted
            total_freed += freed
    
    logger.info(
        f"Total cleanup: {total_deleted} files, "
        f"{total_freed / 1024 / 1024:.2f} MB freed"
    )
    
    return total_deleted, total_freed
