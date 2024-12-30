from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.login import router as login_router
from app.routes.tasa import router as tasa_router
import os

app = FastAPI(
    title="Xepelin Backend API",
    description="API para gestión de tasas",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Configuración CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers sin prefijo
app.include_router(login_router)
app.include_router(tasa_router)

@app.get("/")
async def root():
    return {"message": "API is running"}
