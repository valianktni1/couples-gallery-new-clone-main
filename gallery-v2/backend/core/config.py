import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Couples Gallery V2"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "CHANGE_THIS_SECRET_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Filesystem
    FILES_DIR: str = "files"  # Where images are stored
    THUMBNAILS_DIR: str = "data/thumbnails"
    
    # Database
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "couples_gallery"

    class Config:
        env_file = ".env"

settings = Settings()
