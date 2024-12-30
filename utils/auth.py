from datetime import datetime, timedelta
from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# Configuración de seguridad
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Usuarios de prueba
TEST_USERS = {
    "admin": {
        "username": "admin",
        "password": "password",
        "role": "admin"
    },
    "user1": {
        "username": "user1",
        "password": "password123",
        "role": "user"
    },
    "user2": {
        "username": "user2",
        "password": "password456",
        "role": "user"
    }
}

def authenticate_user(username: str, password: str):
    if username in TEST_USERS and password == TEST_USERS[username]["password"]:
        return TEST_USERS[username]
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Añadimos el rol al token
    if "sub" in to_encode and to_encode["sub"] in TEST_USERS:
        to_encode["role"] = TEST_USERS[to_encode["sub"]]["role"]
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido - no contiene username"
            )
        return {"username": username, "role": role}
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado"
        )

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        user_data = verify_token(token)
        if user_data is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_data
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="No se pudo validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
