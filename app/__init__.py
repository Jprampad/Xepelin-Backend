from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.login import router as login_router
from app.routes.tasa import router as tasa_router
from app.utils.handlers import add_validation_exception_handler
import os

def create_app():
    app = FastAPI(
        title="Xepelin Backend API",
        description="API para gestión de tasas",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json"
    )
    
    # Configuración CORS
    origins = os.getenv('CORS_ORIGINS', '*').split(',')
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Agregar manejador de excepciones
    add_validation_exception_handler(app)
    
    # Agregar routers sin el prefijo /api (ya que se maneja en vercel.json)
    app.include_router(login_router)
    app.include_router(tasa_router)
    
    return app
