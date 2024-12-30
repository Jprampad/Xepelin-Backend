from app import create_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = create_app()

# Configurar CORS específicamente para el endpoint de login
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar el root_path para Vercel
app.root_path = "/api"

# Opcional: Redirigir la raíz a /docs
@app.get("/")
async def root():
    return {"message": "API is running. Visit /docs for documentation"}
