
import os
import requests
from urllib.parse import quote


def get_zoom_token():
    """Obtiene access token de Zoom via Server-to-Server OAuth"""
    account_id    = os.environ["ZOOM_ACCOUNT_ID"]
    client_id     = os.environ["ZOOM_CLIENT_ID"]
    client_secret = os.environ["ZOOM_CLIENT_SECRET"]

    resp = requests.post(
        "https://zoom.us/oauth/token",
        params={"grant_type": "account_credentials", "account_id": account_id},
        auth=(client_id, client_secret)
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def download_recording(download_url, output_path):
    """Descarga la grabación de Zoom al servidor"""
    token = get_zoom_token()
    headers = {"Authorization": f"Bearer {token}"}

    print(f"⬇️  Descargando grabación...")
    with requests.get(download_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Descargado: {output_path} ({size_mb:.1f} MB)")
    return output_path


def get_recording_files(meeting_id):
    """Obtiene los archivos de grabación de una reunión"""
    token = get_zoom_token()
    headers = {"Authorization": f"Bearer {token}"}

    meeting_id_encoded = quote(meeting_id, safe="")

    resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{meeting_id_encoded}/recordings",
        headers=headers
    )
    resp.raise_for_status()
    return resp.json()
