"""Alertas de error — Telegram, Slack y registro en Redis.

Sin canal configurado el sistema falla en silencio: los PDFs igual aparecen en
Drive (el pipeline degrada, no se cae), así que un error de créditos o de
traducción no se nota mirando la carpeta. Por eso además del push se guarda
siempre el registro en Redis, que se consulta en /errores.
"""
import os
import json
from datetime import datetime

ERRORS_KEY = "qualbot:errores"
ERRORS_MAX = 100
ERRORS_TTL = 60 * 60 * 24 * 30  # 30 días


def _redis():
    try:
        import redis
        url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_PRIVATE_URL")
        if url:
            return redis.from_url(url, decode_responses=True, socket_timeout=3)
    except Exception as e:
        print(f"⚠️  Redis no disponible para el registro de errores: {e}")
    return None


def _record(context, error, tb):
    r = _redis()
    if not r:
        return
    try:
        r.lpush(ERRORS_KEY, json.dumps({
            "cuando": datetime.now().isoformat(timespec="seconds"),
            "donde": str(context),
            "error": str(error)[:500],
            "traceback": (tb or "")[-1200:],
        }, ensure_ascii=False))
        r.ltrim(ERRORS_KEY, 0, ERRORS_MAX - 1)
        r.expire(ERRORS_KEY, ERRORS_TTL)
    except Exception as e:
        print(f"⚠️  No se pudo registrar el error en Redis: {e}")


def _telegram(text):
    """Mensaje de texto plano: los tracebacks rompen el parseo de Markdown."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat):
        return False
    try:
        import requests as req
        resp = req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text[:4000],
                  "disable_web_page_preview": True},
            timeout=8)
        if resp.status_code != 200:
            print(f"⚠️  Telegram respondió {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"⚠️  No se pudo notificar a Telegram: {e}")
        return False


def _slack(text):
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        import requests as req
        req.post(url, json={"text": text}, timeout=5)
        return True
    except Exception as e:
        print(f"⚠️  No se pudo notificar a Slack: {e}")
        return False


def notify_error(context, error, tb=""):
    """Avisa por los canales configurados y deja el error registrado."""
    _record(context, error, tb)
    texto = f"❌ QualBot — error en {context}\n\n{error}"
    if tb:
        texto += f"\n\n{tb[-1200:]}"
    enviado = _telegram(texto)
    enviado = _slack(f"❌ *QualBot error* en `{context}`\n```{error}```"
                     + (f"\n```{tb[-1500:]}```" if tb else "")) or enviado
    if not enviado:
        print("⚠️  Sin canal de alertas configurado — el error queda solo en /errores")
    return enviado


def notify(text):
    """Aviso de progreso o hito. No se registra como error."""
    return _telegram(text) or _slack(text)


def carpeta_drive():
    """Link a la carpeta de Drive donde caen los reportes."""
    fid = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    return f"https://drive.google.com/drive/folders/{fid}" if fid else ""


def canales():
    """Qué canales están configurados, para /health."""
    return {
        "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN")
                         and os.environ.get("TELEGRAM_CHAT_ID")),
        "slack": bool(os.environ.get("SLACK_WEBHOOK_URL")),
    }
