from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, gallery, files
from core.config import settings
from core.database import db

app = FastAPI(title=settings.PROJECT_NAME)

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    db.close()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(gallery.router, prefix="/api", tags=["gallery"])
app.include_router(files.router, prefix="/api/files", tags=["files"])

@app.get("/")
async def root():
    return {"message": "Gallery V2 Backend is Running"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

