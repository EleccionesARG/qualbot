import os
import requests

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


def download_recording(download_url, output_path, download_token=""):
    """Descarga la grabación de Zoom al servidor.

    Las URLs webhook_download del evento recording.completed exigen el
    download_token que viene en el payload del webhook (el token OAuth
    server-to-server devuelve 401 ahí). Para URLs obtenidas por API
    (reprocesamiento manual) se usa el token OAuth.
    """
    token = download_token or get_zoom_token()

    # Append access_token como query param (compatible con webhook_download y API regular)
    separator = "&" if "?" in download_url else "?"
    url = f"{download_url}{separator}access_token={token}"

    print(f"⬇️  Descargando grabación...")
    with requests.get(url, stream=True, allow_redirects=True) as r:
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

    resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings",
        headers=headers
    )
    resp.raise_for_status()
    return resp.json()
