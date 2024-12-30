from app import create_app
from fastapi import FastAPI

app = create_app()

# Configurar el root_path para Vercel
app.root_path = "/api"

# Opcional: Redirigir la raíz a /docs
@app.get("/")
async def root():
    return {"message": "API is running. Visit /docs for documentation"}
