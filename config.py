import os

# Modo inglés: con QUALBOT_LANG=en en Railway, cada sesión genera además
# el PDF del análisis en inglés y la transcripción traducida.
QUALBOT_LANG = os.environ.get("QUALBOT_LANG", "es").strip().lower()
ENGLISH_MODE = QUALBOT_LANG == "en"
TRANSLATION_MODEL = os.environ.get("QUALBOT_TRANSLATION_MODEL", "claude-opus-5")
