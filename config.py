import os

# Modo inglés: con QUALBOT_LANG=en en Railway, cada sesión genera además
# el PDF del análisis en inglés y la transcripción traducida.
QUALBOT_LANG = os.environ.get("QUALBOT_LANG", "es").strip().lower()
ENGLISH_MODE = QUALBOT_LANG == "en"
TRANSLATION_MODEL = os.environ.get("QUALBOT_TRANSLATION_MODEL", "claude-opus-5")

# Nombres/términos canónicos de la sesión (marcas, personas, herramientas),
# separados por coma. Se inyectan en análisis y traducción para corregir
# errores de oído del transcriptor (ej. "Opinar, Read.AI, SurveyMonkey").
QUALBOT_GLOSSARY = os.environ.get("QUALBOT_GLOSSARY", "").strip()

# Traducir el análisis al inglés además de la transcripción. Apagado: el
# entregable en inglés es la transcripción; el análisis se lee en castellano.
# Se enciende con QUALBOT_ANALYSIS_EN=1 en Railway.
ANALYSIS_EN = os.environ.get("QUALBOT_ANALYSIS_EN", "0").strip().lower() in (
    "1", "true", "si", "sí", "yes", "on")
