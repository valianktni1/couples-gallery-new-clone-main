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
        # Check a sample file for physical existence
        logger.info("Verifying physical file existence for a sample...")
        sample_file = await db.files.find_one({})
        
        try:
            folder_path = await get_folder_path(db, sample_file['folder_id'], FILES_DIR)
            file_path = folder_path / sample_file['stored_name']
            
            if file_path.exists():
                logger.info(f"✅ Sample file found on disk: {file_path}")
            else:
                logger.error(f"❌ Sample file MISSING on disk: {file_path}")
                logger.info(f"   (This suggests migration didn't run or failed)")
                
                # Check if it exists in old location
                old_path = FILES_DIR / sample_file['stored_name']
                if old_path.exists():
                    logger.info(f"   ⚠️  File found at OLD location: {old_path}")
                    logger.info("       -> You need to run the migration script!")
        except Exception as e:
            logger.error(f"Error checking file path: {e}")

    logger.info("Verification complete.")

if __name__ == "__main__":
    asyncio.run(verify())
