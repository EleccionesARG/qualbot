"""
drive_uploader.py
Sube el reporte PDF a una carpeta de Google Drive compartida
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ID de la carpeta en Google Drive donde se guardan los reportes
# (se configura en variable de entorno)
DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    """Crea el cliente de Google Drive usando credenciales de service account"""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise ValueError("❌ Variable GOOGLE_SERVICE_ACCOUNT_JSON no configurada")

    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)

def upload_report(pdf_path, filename):
    """
    Sube un PDF a Google Drive y retorna el link compartible.
    Si no hay credenciales configuradas, retorna un link vacío (modo desarrollo).
    """
    if not DRIVE_FOLDER_ID:
        print("  ⚠️  GOOGLE_DRIVE_FOLDER_ID no configurado, omitiendo subida")
        return ""

    try:
        service = get_drive_service()

        # Metadata del archivo
        file_metadata = {
            "name": filename,
            "parents": [DRIVE_FOLDER_ID],
            "mimeType": "application/pdf"
        }

        # Subir archivo
        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        file_id   = file.get("id")
        view_link = file.get("webViewLink", "")

        # Hacer el archivo accesible para todos los que tengan el link
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"}
        ).execute()

        print(f"  ✅ Subido a Drive: {view_link}")
        return view_link

    except Exception as e:
        print(f"  ⚠️  Error subiendo a Drive: {e}")
        return ""
