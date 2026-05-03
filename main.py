from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.db import init_db
from services.context import cleanup_expired
from services.exceptions import AppError
from routers import health, context


async def _cleanup_loop():
    while True:
        await asyncio.sleep(600)  # 10 minutes
        cleanup_expired()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="AI Clipboard", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": exc.message},
    )


app.include_router(health.router)
app.include_router(context.router)
