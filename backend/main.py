# ruff: noqa: E402

import os
import sys
from dotenv import load_dotenv

load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.middleware import setup_middlewares
from api.router import api_router
from core.db.connection import init_db

# Directory setup
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Application instantiation
app = FastAPI(title="Hyper Shorts Factory API")

# Setup middlewares (CORS)
setup_middlewares(app)

from core.settings import ASSETS_DIR

# Mount assets directory for frontend
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Include central router
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
def startup_event():
    """Initializes the database on application startup."""
    init_db()
    logger.info("FastAPI application started. Database initialized.")

