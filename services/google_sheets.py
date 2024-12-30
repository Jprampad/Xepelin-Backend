import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException

# Credenciales
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILENAME = 'prueba-xepelin-446012-33bf2851413f.json'
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, CREDENTIALS_FILENAME)
SPREADSHEET_ID = '169UYWpjH7S_-3zEPdKIIt2NhSQ8g9BF3arAwF7edONA'
RANGE_NAME = 'tasas!A2:C9999'

def authenticate_google_sheets():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            available_files = os.listdir(BASE_DIR)
            raise HTTPException(
                status_code=500,
                detail=f"Archivo de credenciales no encontrado. Archivos disponibles: {available_files}"
            )
            
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return build('sheets', 'v4', credentials=creds)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Archivo de credenciales no encontrado en: {SERVICE_ACCOUNT_FILE}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error de autenticación con Google Sheets: {str(e)}"
        )

def get_column_indices(headers):
    """
    Obtiene los índices de las columnas basándose en los encabezados.
    No es sensible a mayúsculas/minúsculas.
    
    Args:
        headers: Lista de encabezados de la hoja

    Returns:
        dict: Diccionario con la posición de cada columna requerida

    Raises:
        HTTPException: Si faltan columnas requeridas o no hay encabezados
    """
    if not headers:
        raise HTTPException(
            status_code=500,
            detail="No se encontraron encabezados en la hoja de cálculo"
        )

    indices = {}
    header_mapping = {
        'idop': 'idOp',
        'tasa': 'tasa',
        'email': 'email'
    }

    for i, header in enumerate(headers):
        header_lower = header.lower().strip()
        if header_lower in header_mapping:
            indices[header_mapping[header_lower]] = i

    # Verificar que se encontraron todas las columnas necesarias
    required_columns = {'idOp', 'tasa', 'email'}
    missing_columns = required_columns - set(indices.keys())
    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=f"Columnas faltantes en la hoja: {', '.join(missing_columns)}"
        )

    return indices

def get_tasas_from_sheet():
    try:
        service = authenticate_google_sheets()
        sheet = service.spreadsheets()
        
        # Obtener todos los datos
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='tasas').execute()
        values = result.get('values', [])
        
        if not values:
            return []
        
        # Obtener los índices de las columnas desde los encabezados
        column_indices = get_column_indices(values[0])
        
        tasas = []
        ids_vistos = set()  # Conjunto para trackear IDs ya procesados
        
        for row in values[1:]:  # Saltar el encabezado
            if len(row) <= max(column_indices.values()):  # Verificar que la fila tenga suficientes columnas
                continue
            
            try:
                idOp = int(row[column_indices['idOp']])
                
                # Si el ID ya fue procesado, saltamos esta fila
                if idOp in ids_vistos:
                    continue
                    
                tasa = float(row[column_indices['tasa']])
                email = row[column_indices['email']]
                
                # Agregar el ID al conjunto de IDs vistos
                ids_vistos.add(idOp)
                
                tasas.append({
                    "idOp": idOp,
                    "tasa": tasa,
                    "email": email
                })
                
            except (ValueError, IndexError) as e:
                continue  # Omitir filas con datos inválidos
        
        return tasas
    except HttpError as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error al acceder a Google Sheets: {str(err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )

def update_tasa_in_sheet(tasa_data):
    try:
        service = authenticate_google_sheets()
        sheet = service.spreadsheets()
        
        # Obtener todos los valores de la hoja
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='tasas').execute()
        values = result.get('values', [])
        
        # Obtener los índices de las columnas
        column_indices = get_column_indices(values[0])
        
        # Buscar la fila con el idOp correspondiente
        for i, row in enumerate(values[1:], start=1):  # start=1 para mantener el índice correcto
            if len(row) <= max(column_indices.values()):
                continue
            
            try:
                if int(row[column_indices['idOp']]) == tasa_data['idOp']:
                    current_tasa = float(row[column_indices['tasa']])
                    if current_tasa == tasa_data['tasa']:
                        return False  # Tasa es la misma
                    
                    # Actualizar la tasa en la columna correcta
                    column_letter = chr(65 + column_indices['tasa'])  # Convertir índice a letra de columna
                    range_name = f'tasas!{column_letter}{i+1}'  # +1 porque i empieza desde 1
                    body = {
                        'values': [[tasa_data['tasa']]]
                    }
                    sheet.values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    return True
            except (ValueError, IndexError):
                continue  # Omitir filas con datos inválidos
                
        return None  # idOp no encontrado
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar Google Sheets: {str(e)}"
        ) 

def insert_tasa_in_sheet(tasa_data):
    """
    Inserta una nueva tasa en la primera fila vacía de Google Sheets.
    
    Args:
        tasa_data: Objeto con idOp, tasa y email
    
    Returns:
        dict: Mensaje de éxito
        
    Raises:
        HTTPException: Si hay error en la inserción o validación
    """
    try:
        service = authenticate_google_sheets()
        sheet = service.spreadsheets()
        
        # Obtener todos los valores
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='tasas'
        ).execute()
        values = result.get('values', [])
        
        if not values:
            raise HTTPException(
                status_code=500,
                detail="No se encontraron datos en la hoja, incluyendo los headers"
            )

        # Obtener los índices de las columnas
        column_indices = get_column_indices(values[0])
        
        # Buscar la primera fila vacía
        primera_fila_vacia = None
        for i, row in enumerate(values[1:], start=2):
            if not row or not any(cell.strip() for cell in row):
                primera_fila_vacia = i
                break
        
        # Si no encontramos fila vacía, usar la siguiente a la última
        if primera_fila_vacia is None:
            primera_fila_vacia = len(values) + 1
            
        # Preparar los datos
        nueva_fila = [""] * len(values[0])  # Inicializar con strings vacíos
        nueva_fila[column_indices['idOp']] = str(tasa_data.idOp)
        nueva_fila[column_indices['tasa']] = str(tasa_data.tasa)
        nueva_fila[column_indices['email']] = str(tasa_data.email)
        
        # Insertar en la primera fila vacía encontrada
        range_name = f'tasas!A{primera_fila_vacia}'
        body = {
            'values': [nueva_fila]
        }
        
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return {"message": "Tasa agregada correctamente"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al agregar la tasa: {str(e)}"
        ) 

def delete_tasa_from_sheet(idOp: int):
    """
    Elimina una tasa de Google Sheets basado en el idOp.
    """
    try:
        service = authenticate_google_sheets()
        sheet = service.spreadsheets()
        
        # Obtener el spreadsheet para obtener el sheet ID
        spreadsheet = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
        
        # Obtener todos los valores
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='tasas'
        ).execute()
        values = result.get('values', [])
        
        if not values:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron datos en la hoja"
            )

        # Obtener los índices de las columnas
        column_indices = get_column_indices(values[0])
        
        # Buscar la fila con el idOp
        fila_a_eliminar = None
        for i, row in enumerate(values[1:], start=2):  # start=2 porque la primera fila son headers
            if len(row) <= column_indices['idOp']:
                continue
                
            try:
                if int(row[column_indices['idOp']]) == idOp:
                    fila_a_eliminar = i
                    break
            except (ValueError, IndexError):
                continue
        
        if fila_a_eliminar is None:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró el registro con ID {idOp}"
            )
            
        # Crear la solicitud para eliminar la fila
        request = {
            'requests': [
                {
                    'deleteDimension': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'ROWS',
                            'startIndex': fila_a_eliminar - 1,  # -1 porque la API usa índices base 0
                            'endIndex': fila_a_eliminar  # endIndex es exclusivo
                        }
                    }
                }
            ]
        }
        
        # Ejecutar la solicitud de eliminación
        sheet.batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=request
        ).execute()
        
        return {"message": f"Registro con ID {idOp} eliminado correctamente"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la tasa: {str(e)}"
        ) 