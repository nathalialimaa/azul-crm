from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from azul_crm.api.routes import router
from azul_crm.application.crm import CustomerNotFound
from azul_crm.bootstrap import Container, build_container
from azul_crm.infrastructure.settings import Settings


def create_app(container: Container | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or build_container(Settings.load())
        yield

    app = FastAPI(title="CRM de Alto Valor — Protótipo privado", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(CustomerNotFound)
    async def missing_customer(request: Request, exc: CustomerNotFound):
        return JSONResponse(status_code=404, content={"detail": "Cliente não encontrado"})

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "demo"}

    app.include_router(router)
    return app


app = create_app()
