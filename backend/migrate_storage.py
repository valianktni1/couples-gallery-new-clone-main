import asyncio
import os
import shutil
import argparse
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
from backend.utils import get_folder_path, get_unique_filename

async def migrate(dry_run=False):
    if dry_run:
        logger.info("🔧 RUNNING IN DRY-RUN MODE. No changes will be made.")
    else:
        logger.info("🚀 Starting storage migration...")
    
    # Get all files
    total_files = await db.files.count_documents({})
    files_cursor = db.files.find({})
    
    processed = 0
    moved = 0
    errors = 0
    skipped = 0
    
    async for file_doc in files_cursor:
        processed += 1
        file_id = file_doc['id']
        file_name = file_doc['name']
        folder_id = file_doc['folder_id']
        stored_name = file_doc.get('stored_name')

        if not stored_name:
             logger.warning(f"File {file_id} has no stored_name. Skipping.")
             errors += 1
             continue
        
        # Source path logic:
        # 1. Check if it's in the root FILES_DIR (old flat structure) using stored_name
        source_path = FILES_DIR / stored_name
        
        # 2. If not found, check if it's using the ID as filename (very old version)
        if not source_path.exists():
            if (FILES_DIR / file_id).exists():
                source_path = FILES_DIR / file_id
                logger.info(f"Found file by ID: {file_id}")
            else:
                # 3. Check if it's already in the correct destination (idempotency)
                try:
                    dest_folder_check = await get_folder_path(db, folder_id, FILES_DIR)
                    expected_path = dest_folder_check / stored_name
                    if expected_path.exists():
                        # Already migrated
                        # logger.debug(f"File already in place: {file_name}")
                        skipped += 1
                        continue
                except Exception:
                    pass

                logger.warning(f"❌ File not found on disk: {file_id} ({file_name}) - Expected at {source_path}")
                errors += 1
                continue
                
        try:
            # Determine destination folder
            dest_folder = await get_folder_path(db, folder_id, FILES_DIR)
            
            # Determine destination file path
            # We want to use the original filename if possible, but safely
            # If we are verifying/fixing, we should check if we need to RENAME it to match DB
            # or if we need to MOVE it.
            
            # Use the filename from DB as the target name
            target_name = file_name
            
            # But wait, if we have multiple files with same name in same folder, 
            # get_unique_filename handles it.
            
            # In dry-run, we just calculate
            if dry_run:
                # Mock destination check
                dest_path = dest_folder / target_name
                if dest_path.exists() and not (source_path.resolve() == dest_path.resolve()):
                     dest_path = dest_folder / f"COPY_{target_name}" # simplified for dry run
            else:
                dest_folder.mkdir(parents=True, exist_ok=True)
                dest_path = get_unique_filename(dest_folder, target_name)
            
            # Check if move is needed
            if source_path.resolve() != dest_path.resolve():
                if dry_run:
                    logger.info(f"[DRY-RUN] Would move: {source_path.name} -> {dest_folder.relative_to(FILES_DIR) / dest_path.name}")
                else:
                    shutil.move(str(source_path), str(dest_path))
                    
                    # Update DB with new stored_name (relative filename in the folder)
                    await db.files.update_one(
                        {'id': file_id},
                        {'$set': {'stored_name': dest_path.name}}
                    )
                    logger.info(f"✅ Migrated: {file_name}")
                moved += 1
            else:
                skipped += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate {file_id}: {e}")
            errors += 1
            
    logger.info(f"Migration complete. Processed: {processed}/{total_files}, Moved: {moved}, Skipped (Already done): {skipped}, Errors: {errors}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate storage to folder structure')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without moving files')
    args = parser.parse_args()
    
    asyncio.run(migrate(dry_run=args.dry_run))
