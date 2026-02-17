from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import aiofiles
from PIL import Image
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from core.database import get_db

router = APIRouter()

FILES_DIR = Path(settings.FILES_DIR)
THUMBNAILS_DIR = Path(settings.THUMBNAILS_DIR)
PREVIEWS_DIR = THUMBNAILS_DIR.parent / "previews" # Matching old structure or config

@router.get("/{file_id}/thumbnail")
async def get_thumbnail(file_id: str):
    # Try WebP first
    thumb_path = THUMBNAILS_DIR / f"{file_id}.webp"
    media_type = "image/webp"
    
    if not thumb_path.exists():
        # Fallback to JPG (if any)
        thumb_path = THUMBNAILS_DIR / f"{file_id}.jpg"
        media_type = "image/jpeg"
        
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
        
    return FileResponse(
        thumb_path, 
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000"}
    )

@router.get("/{file_id}/preview")
async def get_preview(file_id: str):
    # Try WebP first
    preview_path = PREVIEWS_DIR / f"{file_id}.webp"
    media_type = "image/webp"
    
    if not preview_path.exists():
        # Fallback to JPG
        preview_path = PREVIEWS_DIR / f"{file_id}.jpg"
        media_type = "image/jpeg"
        
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview not found")
        
    return FileResponse(
        preview_path, 
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000"}
    )

@router.get("/{file_id}/download")
async def download_file(file_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    file_doc = await db.files.find_one({'id': file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
        
    # We need to resolve the physical path
    # In the new structure, it's FILES_DIR / folder_path / stored_name
    # But wait, how do we get the folder_path reliably?
    # We can use the same helper as in server.py
    
    folder_path = await get_physical_folder_path(db, file_doc['folder_id'], FILES_DIR)
    file_path = folder_path / file_doc['stored_name']
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(file_path, filename=file_doc['name'])

@router.get("/{file_id}/stream")
async def stream_video(file_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    file_doc = await db.files.find_one({'id': file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
        
    folder_path = await get_physical_folder_path(db, file_doc['folder_id'], FILES_DIR)
    file_path = folder_path / file_doc['stored_name']
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(file_path)

@router.post("/public-upload")
async def upload_file_public(
    token: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Verify token
    share = await db.shares.find_one({'token': token})
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share token")
    
    if not share.get('upload_only') and share['permission'] == 'read':
        raise HTTPException(status_code=403, detail="Upload not allowed")
        
    folder_id = share['folder_id']
    
    # Check file type restrictions
    ext = Path(file.filename).suffix.lower()
    allowed_types = share.get('allowed_file_types')
    if allowed_types and ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed.")
    
    file_id = str(uuid.uuid4())
    folder_path = await get_physical_folder_path(db, folder_id, FILES_DIR)
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    target_path = folder_path / file.filename
    counter = 1
    while target_path.exists():
        target_path = folder_path / f"{Path(file.filename).stem} ({counter}){ext}"
        counter += 1
    
    # Save file
    file_size = 0
    async with aiofiles.open(target_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
            file_size += len(chunk)
    
    # Handle image processing
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}
    file_type = 'image' if ext in image_exts else 'video'
    
    if file_type == 'image':
        await generate_thumbnail(target_path, file_id)
        await generate_preview(target_path, file_id)

    file_doc = {
        'id': file_id,
        'name': file.filename,
        'folder_id': folder_id,
        'stored_name': target_path.name,
        'file_type': file_type,
        'size': file_size,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'uploaded_by_share': share['id']
    }
    await db.files.insert_one(file_doc)
    
    return {"id": file_id, "message": "Upload successful"}

# --- Helpers ---

async def generate_thumbnail(file_path: Path, file_id: str):
    try:
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
        with Image.open(file_path) as img:
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            thumb_path = THUMBNAILS_DIR / f"{file_id}.webp"
            img.save(thumb_path, 'WEBP', quality=80)
    except Exception as e:
        print(f"Thumbnail generation failed: {e}")

async def generate_preview(file_path: Path, file_id: str, max_size: int = 1500):
    try:
        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        with Image.open(file_path) as img:
            ratio = min(max_size / img.width, max_size / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            preview_path = PREVIEWS_DIR / f"{file_id}.webp"
            img.save(preview_path, 'WEBP', quality=80)
    except Exception as e:
        print(f"Preview generation failed: {e}")

async def get_physical_folder_path(db, folder_id: str, root_dir: Path) -> Path:
    path_components = []
    current_id = folder_id
    
    while current_id:
        folder = await db.folders.find_one({'id': current_id}, {'name': 1, 'parent_id': 1})
        if not folder: break
        path_components.insert(0, folder['name'])
        current_id = folder.get('parent_id')
        
    return root_dir.joinpath(*path_components)
