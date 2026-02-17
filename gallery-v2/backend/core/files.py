import os
import shutil
from pathlib import Path
from typing import List, Optional
from .config import settings

class FileManager:
    def __init__(self):
        self.base_path = Path(settings.FILES_DIR)
        self.thumbnails_path = Path(settings.THUMBNAILS_DIR)
        
        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)

    def list_folders(self) -> List[str]:
        """List all top-level folders (Couples)"""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]

    def list_files(self, folder_name: str) -> List[str]:
        """List all files in a specific folder"""
        folder = self.base_path / folder_name
        if not folder.exists():
            return []
        
        # Extension filter could go here
        valid_extensions = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}
        return [
            f.name for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in valid_extensions
        ]

    def create_folder(self, folder_name: str) -> bool:
        """Create a new couple folder"""
        path = self.base_path / folder_name
        if path.exists():
            return False
        path.mkdir()
        return True

    def copy_to_favorites(self, folder_name: str, filenames: List[str]) -> int:
        """
        Copy selected files to a 'Favorites' subfolder.
        Returns number of files successfully copied.
        """
        source_dir = self.base_path / folder_name
        target_dir = source_dir / "Favorites"
        target_dir.mkdir(exist_ok=True)
        
        count = 0
        for name in filenames:
            source_file = source_dir / name
            if source_file.exists():
                dest_file = target_dir / name
                if not dest_file.exists():
                    shutil.copy2(source_file, dest_file)
                    count += 1
        return count

file_manager = FileManager()
