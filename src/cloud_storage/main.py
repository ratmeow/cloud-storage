from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from cloud_storage.config import Config
from cloud_storage.ioc import AppProvider
from cloud_storage.logger import setup_package_logger
from cloud_storage.presentation.exceptions import register_exception_handlers
from cloud_storage.presentation.handlers import router
from cloud_storage.presentation.middlewares import register_middlewares


def create_app():
    setup_package_logger()
    config = Config()

    app = FastAPI()
    app.include_router(router)

    register_middlewares(app=app)
    register_exception_handlers(app=app)
    container = make_async_container(AppProvider(), context={Config: config})
    setup_dishka(container=container, app=app)
    return app
