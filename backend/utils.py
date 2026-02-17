import os
import re
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    """
    Remove potentially dangerous characters from filenames.
    Allow alphanumeric, space, dot, underscore, dash.
    """
    # Remove null bytes
    name = name.replace('\0', '')
    # Replace invalid characters with underscore
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing periods and spaces
    name = name.strip('. ')
    if not name:
        name = "unnamed"
    return name

def get_unique_filename(directory: Path, filename: str) -> Path:
    """
    Return a path that doesn't exist in the directory.
    If filename exists, append (1), (2), etc.
    """
    name = sanitize_filename(filename)
    path = directory / name
    
    if not path.exists():
        return path
        
    stem = path.stem
    suffix = path.suffix
    counter = 1
    
    while path.exists():
        new_name = f"{stem} ({counter}){suffix}"
        path = directory / new_name
        counter += 1
        
    return path

async def get_folder_path(db, folder_id: Optional[str], root_dir: Path) -> Path:
    """
    Recursively build the physical path for a folder from the database.
    Querying parents up to the root.
    """
    if not folder_id:
        return root_dir
        
    # Build path components
    # We need to traverse up. This might be slow if deep.
    # Alternatively, use materialized paths if performance is critical.
    # For now, recursive lookup is safe for moderate depth.
    
    path_components = []
    current_id = folder_id
    
    # Preventing infinite loops with a max depth check
    depth = 0
    MAX_DEPTH = 20 
    
    while current_id and depth < MAX_DEPTH:
        folder = await db.folders.find_one({'id': current_id}, {'name': 1, 'parent_id': 1})
        if not folder:
            logger.warning(f"Orphaned folder ID encountered: {current_id}")
            break
            
        path_components.insert(0, sanitize_filename(folder['name']))
        current_id = folder.get('parent_id')
        depth += 1
        
    return root_dir.joinpath(*path_components)
