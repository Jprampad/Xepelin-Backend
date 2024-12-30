from pydantic import BaseModel, EmailStr

class Tasa(BaseModel):
    idOp: int
    tasa: float
    email: EmailStr 