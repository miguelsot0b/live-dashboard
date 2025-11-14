"""
Archivo de Configuración - Dashboard Henniges Automotive
Modifica estos valores según tus necesidades
"""

# ====================================================
# IDs DE ARCHIVOS EN GOOGLE DRIVE
# ====================================================
# Para obtener el ID de un archivo en Google Drive:
# 1. Abre el archivo en Google Drive
# 2. Haz clic en "Compartir" y configura como "Cualquiera con el enlace puede ver"
# 3. Copia el ID de la URL: https://drive.google.com/file/d/ID_AQUI/view

PROD_FILE_ID = "1EhVdt8n6eIjJF0afLm5irDZQv2CDRi7w"
SCRAP_FILE_ID = "1gVbCYSpTNtWE25ZHOPHzDBnkucLIaDN9"
WCLOG_FILE_ID = "1axLJlFa9wIkQS-z_Q1aptfGRjeDPHLwu"
COSTS_FILE_ID = "1PR-G_fanMoPj5YNOv8FuTgh6q9JkjsgP"

# ====================================================
# CONFIGURACIÓN DE TURNOS
# ====================================================
# Formato: hora_inicio (HH, MM), hora_fin (HH, MM)

SHIFTS = {
    "A": {"start": (7, 30), "end": (17, 6)},
    "A + TE": {"start": (7, 30), "end": (19, 30)},  # A con Tiempo Extra hasta 7:30 PM
    "C": {"start": (23, 0), "end": (7, 30)},
    "C + TE": {"start": (19, 30), "end": (7, 30)},  # C con Tiempo Extra entrada a 7:30 PM
    "1": {"start": (7, 30), "end": (15, 30)},
    "2": {"start": (15, 30), "end": (23, 0)},
}

# ====================================================
# CONFIGURACIÓN GENERAL
# ====================================================

# Rate de producción por defecto (piezas/hora)
DEFAULT_RATE = 50

# Tiempo de caché para recargar datos (segundos)
CACHE_TTL = 60

# Número máximo de workcenters a mostrar por defecto
DEFAULT_MAX_WORKCENTERS = 5

# ====================================================
# PALABRAS CLAVE PARA PARADAS PROGRAMADAS
# ====================================================
# Estas palabras en el Status de workcenter logs se consideran paradas programadas
# y NO se cuentan como tiempo muerto
PARADAS_PROGRAMADAS_KEYWORDS = [
    "comida",
    "break",
    "lunch",
    "meal",
    "descanso",
    "break time",
    "almuerzo",
    "cena",
    "coffee break",
    "rest",
    "clockout",  # Cuando sale el operador
]

# ====================================================
# PALABRAS CLAVE PARA STATUS "CORRIENDO"
# ====================================================
# Estos status indican que el equipo está operando normalmente
STATUS_CORRIENDO_KEYWORDS = [
    "corriendo",
    "running",
    "producción",
    "production",
]
