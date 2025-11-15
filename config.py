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

# Horas máximas de producción por turno (excluyendo comida, breaks, etc.)
# Estos valores se usan para calcular la meta acumulada correctamente
HORAS_PRODUCCION_MAXIMAS = {
    "A": 9.1,           # 9.1 horas productivas
    "A + TE": 11.25,    # 11.25 horas productivas con tiempo extra
    "C": 8.0,           # 8.0 horas productivas
    "C + TE": 11.25,    # 11.25 horas productivas con tiempo extra
    "1": 7.5,           # 7.5 horas productivas
    "2": 7.5,           # 7.5 horas productivas
}

# ====================================================
# CONFIGURACIÓN GENERAL
# ====================================================

# Zona horaria de la planta
TIMEZONE = "America/Mexico_City"

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

# ====================================================
# MAPEO DE STATUS A CATEGORÍAS Y COLORES
# ====================================================
# Este mapeo define cómo se clasifican y colorean los diferentes status
# Formato: "status_exacto": {"categoria": "nombre", "color": "hex", "emoji": "icono"}

STATUS_CATEGORIAS = {
    # ===== PRODUCCIÓN ACTIVA =====
    "Idle": {
        "categoria": "🟡 Idle",
        "color": "#f1c40f",
        "orden": 0,
        "es_tiempo_muerto": False
    },
    "Apagado": {
        "categoria": "⚫ Apagado",
        "color": "#95a5a6",
        "orden": 2,
        "es_tiempo_muerto": False
    },
    "Arranque": {
        "categoria": "🟢 Arranque",
        "color": "#27ae60",
        "orden": 3,
        "es_tiempo_muerto": False
    },
    "Producción": {
        "categoria": "🟢 Producción",
        "color": "#2ecc71",
        "orden": 4,
        "es_tiempo_muerto": False
    },
    
    # ===== PARADAS PROGRAMADAS =====
    "Comida": {
        "categoria": "� Comida",
        "color": "#f39c12",
        "orden": 6,
        "es_tiempo_muerto": False
    },
    "Cambio Modelo / Producto": {
        "categoria": "🟡 Cambio Modelo",
        "color": "#e67e22",
        "orden": 8,
        "es_tiempo_muerto": False
    },
    "Cambio de Modelo(SMED)": {
        "categoria": "� Cambio Modelo SMED",
        "color": "#e67e22",
        "orden": 8,
        "es_tiempo_muerto": False
    },
    "Excessive Changeover": {
        "categoria": "🟠 Excessive Changeover",
        "color": "#d35400",
        "orden": 10,
        "es_tiempo_muerto": True
    },
    
    # ===== TIEMPOS MUERTOS =====
    "T.M. por Producción": {
        "categoria": "⚠️ T.M. Producción",
        "color": "#e67e22",
        "orden": 11,
        "es_tiempo_muerto": True
    },
    "T.M. por  Producción  ": {  # Con espacios extras del CSV
        "categoria": "⚠️ T.M. Producción",
        "color": "#e67e22",
        "orden": 11,
        "es_tiempo_muerto": True
    },
    "T.M. por Calidad": {
        "categoria": "⚠️ T.M. Calidad",
        "color": "#e67e22",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "T.M.  por Calidad": {  # Con doble espacio del CSV
        "categoria": "⚠️ T.M. Calidad",
        "color": "#e67e22",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "Defectos de Calidad": {
        "categoria": "⚠️ T.M. Calidad",
        "color": "#e67e22",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "T.M. Falta de Materiales": {
        "categoria": "⛔ Falta Material",
        "color": "#8e44ad",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "Falta de Material en Sistema": {
        "categoria": "⛔ Falta Material",
        "color": "#8e44ad",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "Limite de Scrap": {
        "categoria": "⚠️ Limite Scrap",
        "color": "#e67e22",
        "orden": 12,
        "es_tiempo_muerto": True
    },
    "Falla Servicios Generales Planta": {
        "categoria": "⚡ Falla Servicios",
        "color": "#c0392b",
        "orden": 14,
        "es_tiempo_muerto": True
    },
    
    # ===== MANTENIMIENTO PREVENTIVO =====
    "Mtto. Preventivo Extrusión / Acabados": {
        "categoria": "🔧 Mtto Preventivo",
        "color": "#3498db",
        "orden": 16,
        "es_tiempo_muerto": False
    },
    "MTTO Preventivo Equipos Acabados": {
        "categoria": "🔧 Mtto Preventivo",
        "color": "#3498db",
        "orden": 16,
        "es_tiempo_muerto": False
    },
    "MTTO Preventivo Equipos Extrusion": {
        "categoria": "🔧 Mtto Preventivo",
        "color": "#3498db",
        "orden": 16,
        "es_tiempo_muerto": False
    },
    "MTTO Preventivo Herramentales": {
        "categoria": "🔧 Mtto Preventivo",
        "color": "#3498db",
        "orden": 16,
        "es_tiempo_muerto": False
    },
    
    # ===== MANTENIMIENTO CORRECTIVO - EQUIPO =====
    "Mtto. Correctivo Equipo": {
        "categoria": "🔴 Correctivo Equipo",
        "color": "#e74c3c",
        "orden": 20,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Molde": {
        "categoria": "🔴 Correctivo Molde",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Prensa": {
        "categoria": "🔴 Correctivo Prensa",
        "color": "#c0392b",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Pineadora": {
        "categoria": "🔴 Correctivo Pineadora",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Bender (Dobladora)": {
        "categoria": "🔴 Correctivo Bender",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Cortadora": {
        "categoria": "🔴 Correctivo Cortadora",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Hotmel": {
        "categoria": "� Correctivo Hotmel",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Pesplice": {
        "categoria": "🔴 Correctivo Pesplice",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Poka Yoke": {
        "categoria": "🔴 Correctivo Poka Yoke",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Robot": {
        "categoria": "🔴 Correctivo Robot",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Mtto. Correctivo - Transfer": {
        "categoria": "🔴 Correctivo Transfer",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    "Falla de Poka Yoke": {
        "categoria": "🔴 Correctivo Poka Yoke",
        "color": "#e74c3c",
        "orden": 22,
        "es_tiempo_muerto": True
    },
    
    # ===== EXTRUSIÓN =====
    "Setup Extrusión": {
        "categoria": "🔧 Setup Extrusión",
        "color": "#3498db",
        "orden": 30,
        "es_tiempo_muerto": False
    },
    "Pruebas Extrusión": {
        "categoria": "🔧 Pruebas Extrusión",
        "color": "#3498db",
        "orden": 32,
        "es_tiempo_muerto": False
    },
    "Mtto Correctivo Equipo Extrusión": {
        "categoria": "🔴 Correctivo Extrusión",
        "color": "#e74c3c",
        "orden": 34,
        "es_tiempo_muerto": True
    },
    "Correctivo Procesos Extrusión": {
        "categoria": "🔴 Correctivo Procesos Ext",
        "color": "#e74c3c",
        "orden": 38,
        "es_tiempo_muerto": True
    },
    
    # ===== DADOS Y HERRAMENTALES =====
    "Dados": {
        "categoria": "🔧 Dados",
        "color": "#e74c3c",
        "orden": 36,
        "es_tiempo_muerto": True
    },
    "Dados(Inactive)": {
        "categoria": "🔧 Dados Inactivo",
        "color": "#95a5a6",
        "orden": 36,
        "es_tiempo_muerto": False
    },
    "Afinacion de dados": {
        "categoria": "🔧 Afinación Dados",
        "color": "#3498db",
        "orden": 36,
        "es_tiempo_muerto": False
    },
    
    # ===== ACABADOS =====
    "Setup Acabados": {
        "categoria": "🔧 Setup Acabados",
        "color": "#3498db",
        "orden": 30,
        "es_tiempo_muerto": False
    }
}

# Categoría por defecto para status no mapeados
STATUS_DEFAULT = {
    "categoria": "🔴 Paro No Programado",
    "color": "#e74c3c",
    "orden": 99,
    "es_tiempo_muerto": True
}
