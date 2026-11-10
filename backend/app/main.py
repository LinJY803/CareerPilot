import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router
from app.core.config import settings
from app.core.errors import AppError
from app.services.tasks import task_runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if not settings.careerpilot_testing:
        task_runner.start()
        await task_runner.recover()
    yield
    if not settings.careerpilot_testing:
        await task_runner.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan, redirect_slashes=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.exception_handler(AppError)
async def handle_app_error(_request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
