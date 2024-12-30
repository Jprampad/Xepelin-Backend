from fastapi import APIRouter, HTTPException, Depends, Path, Body, Request
import httpx
from ..models import Tasa
from ..services.google_sheets import (
    get_tasas_from_sheet, 
    update_tasa_in_sheet, 
    authenticate_google_sheets,
    SPREADSHEET_ID,
    insert_tasa_in_sheet,
    delete_tasa_from_sheet
)
from ..utils.auth import get_current_user
from pydantic import Field, BaseModel, EmailStr, validator, conint
from typing import List, Dict, Any
import json

# Cargar documentación
with open('app/docs/documentacion.json') as f:
    docs = json.load(f)

router = APIRouter(
    prefix="/tasas",
    tags=["Tasas"],
    responses={401: {"description": "No autorizado"}}
)

class TasaResponse(BaseModel):
    """Modelo de respuesta para las tasas"""
    idOp: int = Field(..., description="ID de la operación")
    tasa: float = Field(..., description="Valor de la tasa")
    email: str = Field(..., description="Email asociado a la tasa")

class NuevaTasa(BaseModel):
    idOp: int = Field(gt=0, description="ID de operación (debe ser positivo)")
    tasa: float = Field(ge=0, description="Tasa (debe ser mayor o igual a 0)")
    email: EmailStr

    @validator('tasa')
    def validate_tasa_format(cls, v: float) -> float:
        """Validar que la tasa sea positiva y tenga exactamente 2 decimales"""
        if v < 0:
            raise ValueError('La tasa debe ser un número positivo')
        
        return v  # Aseguramos que tenga 2 decimales

    @validator('idOp', pre=True)
    def validate_idop(cls, v: Any) -> int:
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError('El ID de operación debe ser un número entero')
        if not isinstance(v, int):
            raise ValueError('El ID de operación debe ser un número entero')
        if v <= 0:
            raise ValueError('El ID de operación debe ser positivo')
        return v

    @validator('tasa', pre=True)
    def validate_tasa(cls, v: Any) -> float:
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise ValueError('La tasa debe ser un número decimal')
        if not isinstance(v, (int, float)):
            raise ValueError('La tasa debe ser un número decimal')
        return float(v)

@router.get("",
    response_model=List[TasaResponse],
    summary="Obtener todas las tasas",
    responses=docs["tasas"]["get"]
)
async def get_tasas(current_user: str = Depends(get_current_user)):
    """
    Obtiene la lista de tasas con emails válidos desde Google Sheets.

    Este endpoint recupera las tasas almacenadas en la hoja de cálculo que contengan
    emails con formato válido (debe incluir @ y dominio con punto),
    requiere autenticación mediante token JWT.

    Returns:
    - **List[TasaResponse]**: Lista de objetos Tasa con:
        - idOp (int): ID de la operación
        - tasa (float): Valor de la tasa
        - email (str): Email asociado (solo emails con formato válido)

    Raises:
    - **401**: Token inválido o expirado
    - **404**: No se encontraron tasas o no hay tasas con emails válidos
    - **500**: Error interno del servidor

    Note:
    - Las tasas con emails inválidos son automáticamente filtradas de la respuesta
    - Un email válido debe contener @ y al menos un punto en el dominio
    - Si existen múltiples registros con el mismo ID de operación, solo se retorna el primero encontrado
    - El orden de los registros se mantiene según aparecen en la hoja de cálculo
    """
    try:
        tasas = get_tasas_from_sheet()
        if not tasas:
            raise HTTPException(status_code=404, detail="No se encontraron tasas")
        
        # Filtrar solo las tasas con emails válidos
        tasas_validas = [
            tasa for tasa in tasas 
            if tasa.get('email') and '@' in tasa['email'] and '.' in tasa['email'].split('@')[1]
        ]
        
        if not tasas_validas:
            raise HTTPException(status_code=404, detail="No se encontraron tasas con emails válidos")
                
        return tasas_validas
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener las tasas: {str(e)}"
        )

@router.post("/create",
    response_model=dict,
    summary="Agregar un nuevo registro",
    responses=docs["tasas"]["new"]
)
async def crear_tasa(
    tasa: NuevaTasa,
    current_user: str = Depends(get_current_user)
):
    """
    Agrega una nueva tasa a Google Sheets.

    Parameters:
    - **tasa**: Objeto NuevaTasa con:
        - idOp (int): ID de la operación (debe ser único y positivo)
        - tasa (float): Valor de la tasa (debe ser positivo)
        - email (str): Email válido

    Returns:
    - **dict**: Mensaje de éxito indicando que la tasa fue agregada correctamente

    Raises:
    - **400 Bad Request**:
        - ID de operación ya existe en la base de datos
        - ID de operación no es positivo
        - Tasa no es un número decimal positivo
        - Email no tiene un formato válido
    - **401 Unauthorized**:
        - Token JWT no proporcionado
        - Token JWT inválido o expirado
    - **500 Internal Server Error**:
        - Error al conectar con Google Sheets
        - Error de autenticación con Google
        - Error al escribir en la hoja de cálculo
        - Límites de la hoja excedidos
        - Cualquier error inesperado durante el proceso

    Nota:
    - La tasa se agregará en la primera fila vacía encontrada en la hoja
    - Se considera fila vacía aquella que no tiene datos o solo tiene espacios en blanco
    - Si no hay filas vacías, se agregará al final de la hoja
    """
    try:
        # Verificar que el ID no exista
        tasas_existentes = get_tasas_from_sheet()
        if any(t['idOp'] == tasa.idOp for t in tasas_existentes):
            raise HTTPException(
                status_code=400,
                detail=f"El ID de operación {tasa.idOp} ya existe"
            )

        # Insertar la nueva tasa
        return insert_tasa_in_sheet(tasa)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al agregar la tasa: {str(e)}"
        ) 
        
@router.post("/{idOp}", 
    response_model=dict,
    summary="Actualizar una tasa de un ID operación existente",
    responses=docs["tasas"]["update"]
)
async def update_tasa(
    idOp: int = Path(..., description="ID de la operación a actualizar"),
    tasa_update: dict = Body(..., example={"tasa": 10.01, "email": "ejemplo@xepelin.com"}),
    current_user: str = Depends(get_current_user)
):
    """
    Actualiza una tasa específica y envía notificación.

    Este endpoint actualiza el valor de una tasa en Google Sheets y
    envía una notificación a través de Zapier cuando la actualización es exitosa.

    Parameters:
    - **idOp**: ID de la operación a actualizar (path parameter)
    - **tasa_update**: Objeto con:
        - tasa (float): Nuevo valor de la tasa (debe ser positivo)
        - email (str): Email del usuario que realiza la actualización

    Returns:
    - **dict**: Mensaje de éxito con:
        - message (str): Descripción del resultado de la operación

    Raises:
    - **400**: Tasa negativa
    - **401**: Token inválido
    - **404**: ID de operación no encontrado
    - **500**: Error en Zapier o error interno
    """
    try:
        # Validar tasa
        if tasa_update["tasa"] < 0:
            raise HTTPException(
                status_code=400,
                detail="La tasa no puede ser un número negativo"
            )
        
        # Crear objeto Tasa completo
        tasa_completa = {
            "idOp": idOp,
            "tasa": tasa_update["tasa"],
            "email": tasa_update["email"]
        }
        
        result = update_tasa_in_sheet(tasa_completa)
        
        if result is None:
            raise HTTPException(
                status_code=404, 
                detail=f"idOp {idOp} no encontrado en Google Sheets"
            )
        
        elif result is False:
            return {
                "message": f"La tasa para idOp {idOp} ya es la misma, no se actualizó."
            }
        
        # Enviar notificación a Zapier
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hooks.zapier.com/hooks/catch/6872019/oahrt5g/",
                json={
                    'idOp': idOp,
                    'tasa': tasa_update["tasa"],
                    'email': tasa_update["email"]
                }
            )
            
            if response.status_code == 200:
                return {"message": "Tasa actualizada correctamente y notificación enviada"}
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="Error al enviar la notificación a Zapier"
                )
                
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        ) 

@router.delete("/{idOp}",
    response_model=dict,
    summary="Eliminar un id operación existente",
    responses=docs["tasas"]["delete"]
)
async def delete_tasa(
    idOp: int = Path(..., description="ID de la operación a eliminar", gt=0),
    current_user: str = Depends(get_current_user)
):
    """
    Elimina una ID Operación específica de Google Sheets.

    Parameters:
    - **idOp**: ID de la operación a eliminar (debe ser positivo)

    Returns:
    - **dict**: Mensaje de éxito

    Raises:
    - **404**: ID de operación no encontrado
    - **401**: Token inválido o expirado
    - **500**: Error interno del servidor
    """
    try:
        return delete_tasa_from_sheet(idOp)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        ) 

