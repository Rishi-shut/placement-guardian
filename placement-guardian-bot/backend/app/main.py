import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import webhook_router, auth_router, bot_router
from app.services import init_firebase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Placement Guardian Bot...")
    
    try:
        init_firebase()
        logger.info("Firebase initialized")
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")
    
    try:
        from app.routers.bot import setup_webhook
        await setup_webhook()
        logger.info("Telegram webhook setup complete")
    except Exception as e:
        logger.error(f"Failed to setup telegram webhook: {e}")
    
    logger.info("Application started successfully")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title="Placement Guardian Bot API",
    description="Telegram bot for monitoring placement emails",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(bot_router)


@app.get("/")
async def root():
    return {
        "service": "Placement Guardian Bot",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
