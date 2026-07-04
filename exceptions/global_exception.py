import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

def register_exception_handlers(app):
    @app.exception_handler(Exception)
    def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong. Please try again later."}
        )