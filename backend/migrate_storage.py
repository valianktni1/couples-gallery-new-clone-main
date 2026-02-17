import asyncio
import os
import shutil
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# DB Setup
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Paths
FILES_DIR = Path(os.environ.get('FILES_DIR', '/app/files'))

# Import Utils
import sys
sys.path.append(str(ROOT_DIR.parent))
from backend.utils import get_folder_path, get_unique_filename, sanitize_filename

async def migrate():
    logger.info("Starting storage migration...")
    
    # Get all files
    files_cursor = db.files.find({})
    total_files = await db.files.count_documents({})
    processed = 0
    moved = 0
    errors = 0
    
    async for file_doc in files_cursor:
        processed += 1
        file_id = file_doc['id']
        file_name = file_doc['name']
        folder_id = file_doc['folder_id']
        stored_name = file_doc['stored_name']
        
        # Source path (flat structure using UUID or stored_name)
        source_path = FILES_DIR / stored_name
        
        if not source_path.exists():
            # Try to find it by ID (older version might use ID only)
            if (FILES_DIR / file_id).exists():
                source_path = FILES_DIR / file_id
            else:
                logger.warning(f"File not found on disk: {file_id} ({file_name})")
                errors += 1
                continue
                
        try:
            # Determine destination folder
            dest_folder = await get_folder_path(db, folder_id, FILES_DIR)
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            # Determine destination file path
            # We want to use the original filename
            dest_path = get_unique_filename(dest_folder, file_name)
            
            # Move file
            if source_path.resolve() != dest_path.resolve():
                shutil.move(str(source_path), str(dest_path))
                moved += 1
                
                # Update DB with new stored_name (which is just the filename now, relative to folder)
                # Actually, server.py uses `stored_name` as filename only?
                # Let's check server.py logic:
                # stored_name = file_path.name
                # And retrieval: Does server.py use stored_name to find file?
                # delete_file: file_path = FILES_DIR / f['stored_name'] <-- ERROR IN SERVER.PY?
                # Wait, if I change storage to nested, `FILES_DIR / stored_name` is WRONG if stored_name is just filename!
                # I need to FIX server.py deletion logic too!
                
                # But for now, let's update DB with just the filename
                await db.files.update_one(
                    {'id': file_id},
                    {'$set': {'stored_name': dest_path.name}}
                )
                
            logger.info(f"Migrated: {file_name} -> {dest_folder.relative_to(FILES_DIR) / dest_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to migrate {file_id}: {e}")
            errors += 1
            
    logger.info(f"Migration complete. Processed: {processed}, Moved: {moved}, Errors: {errors}")

if __name__ == "__main__":
    asyncio.run(migrate())
