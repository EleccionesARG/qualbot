import os
import json

def upload_report(pdf_path, filename):
    folder_id  = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not folder_id or not creds_json:
        print("Drive no configurado, omitiendo subida")
        return ""

    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds   = service_account.Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds)
    meta    = {"name": filename, "parents": [folder_id]}
    media   = MediaFileUpload(pdf_path, mimetype="application/pdf")
    f       = service.files().create(body=meta, media_body=media,
                                      fields="id,webViewLink").execute()
    service.permissions().create(
        fileId=f["id"], body={"type": "anyone", "role": "reader"}
    ).execute()
    return f.get("webViewLink", "")
