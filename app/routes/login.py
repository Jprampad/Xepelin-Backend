from fastapi import APIRouter, HTTPException, status, Response
from ..utils.auth import authenticate_user, create_access_token
from ..models.auth_models import Token, LoginRequest
from pydantic import Field
import json
from pathlib import Path

# Cargar documentación
docs_path = Path(__file__).parent.parent / "docs" / "documentacion.json"
with open(docs_path) as f:
    docs = json.load(f)

router = APIRouter()

class LoginResponse(Token):
    """Modelo de respuesta para el login exitoso"""
    access_token: str = Field(..., description="Token JWT para autenticación")
    token_type: str = Field("bearer", description="Tipo de token (siempre 'bearer')")

@router.post("/api/login", 
    response_model=LoginResponse,
    summary="Autenticación de usuario",
    responses=docs["auth"]["login"]
)
async def login(credentials: LoginRequest, response: Response):
    """
    Endpoint para autenticar usuarios y obtener un token JWT.

    Este endpoint verifica las credenciales del usuario y, si son válidas,
    genera un token JWT para autenticación posterior.
    """
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}