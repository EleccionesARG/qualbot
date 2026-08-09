"""Alertas a Slack — compartido entre server y analyzer."""
import os


def notify_error(context, error, tb=""):
    """Envía alerta a Slack si SLACK_WEBHOOK_URL está configurado."""
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    try:
        import requests as req
        text = f"❌ *QualBot error* en `{context}`\n```{error}```"
        if tb:
            text += f"\n```{tb[-1500:]}```"
        req.post(url, json={"text": text}, timeout=5)
    except Exception as e:
        print(f"⚠️  No se pudo notificar a Slack: {e}")
