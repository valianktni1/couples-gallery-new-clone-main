from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from core import security
from core.files import file_manager
from core.database import get_db
from routers.auth import get_current_user, User

router = APIRouter()

# --- Models ---
class Folder(BaseModel):
    id: str
    name: str
    file_count: int = 0
    subfolder_count: int = 0

class FileItem(BaseModel):
    id: str
    name: str
    url: str
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    file_type: str # 'image' or 'video'

class GalleryResponse(BaseModel):
    folder_id: str
    folder_name: str
    permission: str
    upload_only: bool = False
    allowed_file_types: Optional[List[str]] = None

class SelectFavoritesRequest(BaseModel):
    folder_name: str
    filenames: List[str]

# --- Helpers ---
async def is_folder_in_share(db, folder_id: str, root_folder_id: str) -> bool:
    if folder_id == root_folder_id:
        return True
    current_id = folder_id
    while current_id:
        folder = await db.folders.find_one({'id': current_id}, {'_id': 0})
        if not folder:
            return False
        if folder.get('parent_id') == root_folder_id:
            return True
        current_id = folder.get('parent_id')
    return False

# --- Admin Endpoints ---

@router.get("/folders", response_model=List[Folder])
async def list_folders(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """List all top-level folders for Admin"""
    folders = await db.folders.find({'parent_id': None}, {'_id': 0}).to_list(1000)
    result = []
    for f in folders:
        file_count = await db.files.count_documents({'folder_id': f['id']})
        subfolder_count = await db.folders.count_documents({'parent_id': f['id']})
        result.append(Folder(**f, file_count=file_count, subfolder_count=subfolder_count))
    return result

# --- Public Gallery Endpoints (Token-based) ---

@router.get("/gallery/{token}", response_model=GalleryResponse)
async def get_gallery_by_token(token: str, db = Depends(get_db)):
    share = await db.shares.find_one({'token': token}, {'_id': 0})
    if not share:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    folder = await db.folders.find_one({'id': share['folder_id']}, {'_id': 0})
    if not folder:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    return GalleryResponse(
        folder_id=folder['id'],
        folder_name=folder['name'],
        permission=share['permission'],
        upload_only=share.get('upload_only', False),
        allowed_file_types=share.get('allowed_file_types')
    )

@router.get("/gallery/{token}/folders", response_model=List[Folder])
async def get_gallery_folders(token: str, parent_id: Optional[str] = None, db = Depends(get_db)):
    share = await db.shares.find_one({'token': token}, {'_id': 0})
    if not share:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    target_parent = parent_id or share['folder_id']
    
    # Verify access
    if parent_id and not await is_folder_in_share(db, parent_id, share['folder_id']):
        raise HTTPException(status_code=403, detail="Access denied")
        
    folders = await db.folders.find({'parent_id': target_parent}, {'_id': 0}).to_list(1000)
    result = []
    for f in folders:
        file_count = await db.files.count_documents({'folder_id': f['id']})
        subfolder_count = await db.folders.count_documents({'parent_id': f['id']})
        result.append(Folder(**f, file_count=file_count, subfolder_count=subfolder_count))
    return result

@router.get("/gallery/{token}/files")
async def get_gallery_files(
    token: str, 
    folder_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    db = Depends(get_db)
):
    share = await db.shares.find_one({'token': token}, {'_id': 0})
    if not share:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    target_folder = folder_id or share['folder_id']
    
    # Verify access
    if folder_id and not await is_folder_in_share(db, folder_id, share['folder_id']):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if share.get('upload_only'):
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}
    
    skip = (page - 1) * limit
    files = await db.files.find({'folder_id': target_folder}, {'_id': 0}).skip(skip).limit(limit).to_list(limit)
    total_files = await db.files.count_documents({'folder_id': target_folder})
    
    result = []
    for f in files:
        thumbnail_url = None
        preview_url = None
        if f['file_type'] == 'image':
            thumbnail_url = f"/api/files/{f['id']}/thumbnail"
            preview_url = f"/api/files/{f['id']}/preview"
        result.append({
            'id': f['id'],
            'name': f['name'],
            'folder_id': f['folder_id'],
            'file_type': f['file_type'],
            'size': f['size'],
            'created_at': f['created_at'],
            'thumbnail_url': thumbnail_url,
            'preview_url': preview_url
        })
    
    return {
        "items": result,
        "total": total_files,
        "page": page,
        "limit": limit,
        "pages": (total_files + limit - 1) // limit
    }

@router.get("/gallery/{token}/path")
async def get_gallery_path(token: str, folder_id: str, db = Depends(get_db)):
    share = await db.shares.find_one({'token': token}, {'_id': 0})
    if not share:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    path = []
    current_id = folder_id
    # Traverse up until the share root
    while current_id and current_id != share['folder_id']:
        folder = await db.folders.find_one({'id': current_id}, {'_id': 0})
        if not folder: break
        path.insert(0, {'id': folder['id'], 'name': folder['name']})
        current_id = folder.get('parent_id')
    
    # Add root folder
    root_folder = await db.folders.find_one({'id': share['folder_id']}, {'_id': 0})
    if root_folder:
        path.insert(0, {'id': root_folder['id'], 'name': root_folder['name']})
    
    return path

@router.post("/favorites", status_code=status.HTTP_201_CREATED)
async def save_favorites(request: SelectFavoritesRequest):
    """Copy selected files to the 'Favorites' subfolder."""
    count = file_manager.copy_to_favorites(request.folder_name, request.filenames)
    return {"message": f"Successfully saved {count} favorites", "count": count}
