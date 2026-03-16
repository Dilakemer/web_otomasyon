from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from database import get_grouped_price_history, init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield



app = FastAPI(title="Trendyol Fiyat Takip API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/urunler")
async def get_products(urun_url: str | None = Query(default=None)) -> dict[str, object]:
    products = get_grouped_price_history(urun_url=urun_url)
    # Her ürün için satıcılar ayrı listelenir
    return {
        "adet": len(products),
        "urunler": products,
    }
