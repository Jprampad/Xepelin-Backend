from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import List, Dict, Any

def format_validation_error(error: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea un error de validación para que sea JSON serializable"""
    return {
        "type": error.get("type", "validation_error"),
        "loc": error.get("loc", []),
        "msg": str(error.get("msg", "")),
        "input": error.get("input"),
        "ctx": {
            "error": str(error.get("ctx", {}).get("error", ""))
        } if error.get("ctx") else None
    }

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Manejador personalizado para errores de validación
    """
    errors = [format_validation_error(error) for error in exc.errors()]
    
    return JSONResponse(
        status_code=422,
        content={
            "message": "Error de validación en los datos enviados",
            "errors": errors,
            "received_data": exc.body if hasattr(exc, 'body') else None
        }
    )

def add_validation_exception_handler(app):
    """
    Agrega el manejador de excepciones a la aplicación
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler) 