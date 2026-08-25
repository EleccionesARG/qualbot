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

    Zoom autentica distinto según de dónde salga la URL: las webhook_download
    del evento recording.completed quieren el download_token del webhook, y las
    que devuelve la API quieren el token OAuth server-to-server. Como un token
    equivocado da 401 y no hay forma de saber de antemano cuál corresponde, se
    prueban las combinaciones en orden hasta que una responde.
    """
    intentos = []
    if download_token:
        intentos += [("download_token del webhook (query)", download_token, "query"),
                     ("download_token del webhook (header)", download_token, "header")]
    intentos += [("OAuth server-to-server (query)", None, "query"),
                 ("OAuth server-to-server (header)", None, "header")]

    oauth = None
    ultimo_error = None
    for nombre, token, modo in intentos:
        if token is None:
            oauth = oauth or get_zoom_token()
            token = oauth
        url, headers = download_url, {}
        if modo == "query":
            sep = "&" if "?" in download_url else "?"
            url = f"{download_url}{sep}access_token={token}"
        else:
            headers = {"Authorization": f"Bearer {token}"}

        print(f"⬇️  Descargando grabación — {nombre}...")
        try:
            with requests.get(url, headers=headers, stream=True,
                              allow_redirects=True, timeout=(30, 600)) as r:
                if r.status_code in (401, 403):
                    ultimo_error = f"{r.status_code} con {nombre}"
                    print(f"↩️  {ultimo_error}, probando la siguiente forma")
                    continue
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except requests.exceptions.HTTPError as e:
            ultimo_error = f"{e} con {nombre}"
            print(f"↩️  {ultimo_error}, probando la siguiente forma")
            continue

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ Descargado: {output_path} ({size_mb:.1f} MB) — {nombre}")
        return output_path

    raise RuntimeError(f"Zoom rechazó la descarga por todas las vías. Último: {ultimo_error}")


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


def _encode_uuid(uuid):
    """Los UUID de Zoom que empiezan con / o contienen // van doble-encodeados."""
    from urllib.parse import quote
    u = quote(str(uuid), safe="")
    if str(uuid).startswith("/") or "//" in str(uuid):
        u = quote(u, safe="")
    return u


def get_meeting_participants(uuid="", meeting_id=""):
    """Nombres de quienes estuvieron en la reunión, según Zoom.

    Es el padrón real: son los nombres que Claudia les pone al entrar, así que
    manda sobre cualquier lista del brief. Reemplaza lo único que aportaba
    Read.ai que Scribe no puede dar. Devuelve [] si la app no tiene el permiso
    o si Zoom no lo conoce — el resto del pipeline sigue igual.
    """
    token = get_zoom_token()
    headers = {"Authorization": f"Bearer {token}"}
    intentos = []
    if uuid:
        u = _encode_uuid(uuid)
        intentos += [f"https://api.zoom.us/v2/report/meetings/{u}/participants",
                     f"https://api.zoom.us/v2/past_meetings/{u}/participants"]
    if meeting_id:
        intentos += [f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants",
                     f"https://api.zoom.us/v2/past_meetings/{meeting_id}/participants"]

    detalle = []
    for url in intentos:
        try:
            r = requests.get(url, headers=headers,
                             params={"page_size": 300}, timeout=30)
            if r.status_code != 200:
                via = url.split("/v2/")[1].split("/participants")[0]
                detalle.append(f"{via} → {r.status_code}: {r.text[:160]}")
                print(f"↩️  Padrón {via} → {r.status_code} {r.text[:160]}")
                continue
            nombres, vistos = [], set()
            for p in r.json().get("participants", []):
                n = (p.get("name") or "").strip()
                if n and n.lower() not in vistos:
                    vistos.add(n.lower())
                    nombres.append(n)
            if nombres:
                print(f"👥 Padrón de Zoom ({len(nombres)}): {', '.join(nombres)}")
                return nombres
        except Exception as e:
            print(f"⚠️  Error pidiendo el padrón: {e}")
    print("⚠️  Sin padrón de Zoom — el mapeo usa solo el brief")
    get_meeting_participants.ultimo_detalle = detalle
    return []
