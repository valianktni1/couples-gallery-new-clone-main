from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.DB_NAME]
        print(f"Connected to MongoDB at {settings.MONGO_URL}")

    def close(self):
        if self.client:
            self.client.close()

db = Database()

async def get_db():
    return db.db
