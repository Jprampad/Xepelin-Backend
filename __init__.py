from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.login import router as login_router
from app.routes.tasa import router as tasa_router
from app.utils.handlers import add_validation_exception_handler

def create_app():
    app = FastAPI()
    
    # Configuración más específica de CORS
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:8000"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Agregar manejador de excepciones
    add_validation_exception_handler(app)
    
    app.include_router(login_router)
    app.include_router(tasa_router)

    
    return app
