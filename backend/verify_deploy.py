import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env from .env file or environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# DB Setup
mongo_url = os.environ.get('MONGO_URL', "mongodb://root:example@mongo:27017")
db_name = os.environ.get('DB_NAME', "gallery")
FILES_DIR = Path(os.environ.get('FILES_DIR', '/app/files'))

# Import Utils
sys.path.append(str(ROOT_DIR.parent))
from backend.utils import get_folder_path

async def verify():
    logger.info("Starting verification...")
    logger.info(f"Connecting to MongoDB at {mongo_url}...")
    
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.server_info()
        logger.info("✅ MongoDB connected.")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return

    db = client[db_name]
    
    # Check Folders
    folder_count = await db.folders.count_documents({})
    logger.info(f"Checking folders... Found {folder_count} folders in DB.")
    
    # Check Files
    file_count = await db.files.count_documents({})
    logger.info(f"Checking files... Found {file_count} files in DB.")
    
    if file_count > 0:
        logger.info("Verifying all files...")
        missing = 0
        found = 0
        
        async for file_doc in db.files.find({}):
            try:
                folder_path = await get_folder_path(db, file_doc['folder_id'], FILES_DIR)
                file_path = folder_path / file_doc['stored_name']
                
                if file_path.exists():
                    found += 1
                else:
                    missing += 1
                    logger.error(f"❌ MISSING: {file_doc['name']} (ID: {file_doc['id']})")
                    logger.error(f"   Expected at: {file_path}")
            except Exception as e:
                logger.error(f"Error checking file {file_doc.get('id')}: {e}")
                missing += 1

        logger.info("-" * 40)
        logger.info(f"Verification Summary:")
        logger.info(f"✅ Found: {found}")
        if missing > 0:
            logger.info(f"❌ Missing: {missing}")
            logger.info("Recommendation: Run 'python backend/migrate_storage.py' to fix paths.")
        else:
            logger.info("🎉 All files verified successfully!")
    else:
        logger.info("No files to verify.")

    logger.info("Verification complete.")

if __name__ == "__main__":
    asyncio.run(verify())
