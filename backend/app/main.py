import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache.investor_cache import set_public_investors
from app.config import get_settings
from app.routers import investors
from app.services.data_loader import load_public_investors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Loading public investor data...")
        records = await load_public_investors()
        set_public_investors(records)
        logger.info(f"Loaded {len(records)} public investors into memory")
    except Exception as e:
        logger.error(f"Startup data load failed (app will still start): {e}")
    yield


app = FastAPI(title="Investor Matcher API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investors.router, prefix="/api")


@app.get("/health")
async def health():
    from app.cache.investor_cache import get_public_investors
    supplement_count = len(get_public_investors())
    return {"status": "ok", "excel_supplement_count": supplement_count, "mode": "dynamic_ai"}
