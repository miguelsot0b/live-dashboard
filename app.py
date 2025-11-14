"""
Dashboard de Producción - Henniges Automotive
Aplicación Streamlit para monitoreo en tiempo real de producción, scrap y status de workcenters
"""

import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from typing import Optional
import altair as alt
import config  # Importar configuración externa
import time as time_module  # Para el sleep
from zoneinfo import ZoneInfo  # Para manejo de zonas horarias

# ====================================================
# CONFIGURACIÓN DE LA PÁGINA
# ====================================================
st.set_page_config(
    page_title="Dashboard Henniges Automotive",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar oculto por defecto
)

# CSS global para compactar diseño (1080p optimizado)
st.markdown("""
    <style>
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    h1, h2, h3, h4 {
        margin-top: 0px;
        margin-bottom: 5px;
    }
    .stMarkdown {
        margin-bottom: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# ====================================================
# CARGAR CONFIGURACIÓN DESDE config.py
# ====================================================
PROD_FILE_ID = config.PROD_FILE_ID
SCRAP_FILE_ID = config.SCRAP_FILE_ID
WCLOG_FILE_ID = config.WCLOG_FILE_ID
COSTS_FILE_ID = config.COSTS_FILE_ID

# Convertir tuplas de turnos a objetos time()
SHIFTS = {
    shift: {
        "start": time(*info["start"]),
        "end": time(*info["end"])
    }
    for shift, info in config.SHIFTS.items()
}

# ====================================================
# FUNCIONES UTILITARIAS
# ====================================================

@st.cache_data(ttl=config.CACHE_TTL)
def load_csv_from_drive(file_id: str) -> pd.DataFrame:
    """
    Carga un archivo CSV desde Google Drive usando su file_id.
    Los datos se cachean por 60 segundos para recargas automáticas.
    Intenta múltiples encodings para manejar diferentes formatos.
    """
    url = f"https://drive.google.com/uc?id={file_id}"
    
    # Intentar diferentes encodings
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            return pd.read_csv(url, encoding=encoding)
        except (UnicodeDecodeError, Exception):
            continue
    
    # Si ninguno funciona, intentar con detección automática
    return pd.read_csv(url, encoding='latin-1')


@st.cache_data(ttl=config.CACHE_TTL)
def load_csv_local(file_path: str) -> pd.DataFrame:
    """
    Carga un archivo CSV local.
    Los datos se cachean para mejorar el rendimiento.
    """
    return pd.read_csv(file_path, encoding='latin-1')


def get_shift_for_timestamp(ts: datetime) -> Optional[str]:
    """
    Determina el turno correspondiente a un timestamp dado.
    Retorna el código del turno ("A", "C", "1", "2") o None si no coincide.
    """
    t = ts.time()
    for shift, info in SHIFTS.items():
        start = info["start"]
        end = info["end"]
        if start < end:
            if start <= t < end:
                return shift
        else:
            if t >= start or t < end:
                return shift
    return None


def horas_transcurridas_en_turno(fecha: datetime.date, turno: str, ahora: datetime) -> float:
    """
    Calcula las horas transcurridas en un turno específico hasta el momento actual.
    NO descuenta paradas programadas ya que están contempladas en la duración del turno.
    
    Args:
        fecha: Fecha del turno (fecha de inicio del turno)
        turno: Código del turno ("A", "C", "1", "2")
        ahora: Timestamp actual (naive datetime en hora local de México)
    
    Returns:
        Horas transcurridas (float)
    """
    info = SHIFTS[turno]
    start_t = info["start"]
    end_t = info["end"]
    
    # Crear datetime de inicio del turno (naive, hora local)
    start_dt = datetime.combine(fecha, start_t)
    
    # Si el turno cruza medianoche (start > end), el fin es al día siguiente
    if start_t > end_t:
        end_dt = datetime.combine(fecha + timedelta(days=1), end_t)
    else:
        end_dt = datetime.combine(fecha, end_t)
    
    # Si aún no ha comenzado el turno
    if ahora < start_dt:
        return 0.0
    
    # Si el turno ya terminó
    if ahora > end_dt:
        return (end_dt - start_dt).total_seconds() / 3600
    
    # El turno está en progreso
    return (ahora - start_dt).total_seconds() / 3600


def calcular_tiempo_muerto(df_wclog_f: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el tiempo muerto por workcenter basado en los logs.
    Usa la columna "Hours" si está disponible, sino calcula diferencias entre timestamps.
    Para el último registro de cada workcenter, calcula hasta "ahora".
    
    Args:
        df_wclog_f: DataFrame filtrado de workcenter logs
    
    Returns:
        DataFrame con columna adicional 'duracion_min' indicando minutos en cada estado
    """
    df = df_wclog_f.sort_values(["workcenter", "timestamp"]).copy()
    
    # Si existe la columna "Hours" (duración en decimal), usarla directamente
    if "Hours" in df.columns:
        # Convertir horas decimales a minutos
        df["duracion_min"] = pd.to_numeric(df["Hours"], errors="coerce").fillna(0) * 60
    else:
        # Calcular por diferencia de timestamps
        df["timestamp_sig"] = df.groupby("workcenter")["timestamp"].shift(-1)
        
        # Para registros que tienen siguiente timestamp, calcular diferencia normal
        mask_con_siguiente = df["timestamp_sig"].notna()
        df.loc[mask_con_siguiente, "duracion_min"] = (
            df.loc[mask_con_siguiente, "timestamp_sig"] - df.loc[mask_con_siguiente, "timestamp"]
        ).dt.total_seconds() / 60
        
        # Para el último registro de cada workcenter (sin siguiente), calcular hasta ahora
        mask_sin_siguiente = df["timestamp_sig"].isna()
        # Obtener hora actual de México como naive datetime
        tz = ZoneInfo(config.TIMEZONE)
        ahora = datetime.now(tz).replace(tzinfo=None)
        
        # Calcular duración desde el timestamp hasta ahora
        df.loc[mask_sin_siguiente, "duracion_min"] = (
            ahora - df.loc[mask_sin_siguiente, "timestamp"]
        ).dt.total_seconds() / 60
        
        # Asegurar que no haya valores negativos
        df["duracion_min"] = df["duracion_min"].clip(lower=0)
    
    return df


def preparar_datos(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """
    Prepara y normaliza los datos de los CSVs.
    
    Args:
        df: DataFrame crudo
        tipo: Tipo de datos ("prod", "scrap", "wclog")
    
    Returns:
        DataFrame preparado con columnas normalizadas
    """
    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Crear timestamp según el tipo de archivo
    if tipo == "prod":
        # Production History usa "Date" con formato "11/10/2025, 3:55 PM" o M/D/YYYY HH:MM
        if "Date" in df.columns:
            # Limpiar comillas si existen
            df["Date"] = df["Date"].astype(str).str.replace('"', '')
            
            # Intentar parsear con infer_datetime_format para manejar múltiples formatos
            df["timestamp"] = pd.to_datetime(df["Date"], errors="coerce", infer_datetime_format=True)
            
            # Si aún hay NaT, intentar formatos específicos
            mask_nat = df["timestamp"].isna()
            if mask_nat.any():
                # Intentar formato M/D/YYYY, H:MM AM/PM
                df.loc[mask_nat, "timestamp"] = pd.to_datetime(
                    df.loc[mask_nat, "Date"], 
                    format="%m/%d/%Y, %I:%M %p",
                    errors="coerce"
                )
            
            # Si aún hay NaT, intentar formato sin coma
            mask_nat = df["timestamp"].isna()
            if mask_nat.any():
                df.loc[mask_nat, "timestamp"] = pd.to_datetime(
                    df.loc[mask_nat, "Date"], 
                    format="%m/%d/%Y %I:%M %p",
                    errors="coerce"
                )
        # Ya tiene "Workcenter"
        if "Workcenter" in df.columns:
            df["workcenter"] = df["Workcenter"].astype(str).str.strip()
        # Normalizar columna de cantidad
        if "Quantity" in df.columns:
            df["Prod"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
            
    elif tipo == "scrap":
        # Scrap Logs usa "Report Date" y "Time Scrapped"
        if "Report Date" in df.columns and "Time Scrapped" in df.columns:
            # Combinar fecha y hora
            fecha_hora_str = df["Report Date"].astype(str) + " " + df["Time Scrapped"].astype(str)
            # Intentar parsear con formato flexible
            df["timestamp"] = pd.to_datetime(fecha_hora_str, errors="coerce", infer_datetime_format=True)
            
            # Si hay NaT, intentar formato específico M/D/YYYY H:MM AM/PM
            mask_nat = df["timestamp"].isna()
            if mask_nat.any():
                df.loc[mask_nat, "timestamp"] = pd.to_datetime(
                    fecha_hora_str[mask_nat], 
                    format="%m/%d/%Y %I:%M %p",
                    errors="coerce"
                )
        # Ya tiene "Workcenter"
        if "Workcenter" in df.columns:
            df["workcenter"] = df["Workcenter"].astype(str).str.strip()
        # Normalizar columna de cantidad de scrap
        if "Quantity" in df.columns:
            df["Scrap Qty"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
        # Limpiar y convertir Extended Cost (quitar $ y comas)
        if "Extended Cost" in df.columns:
            df["Extended Cost"] = df["Extended Cost"].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
            df["Extended Cost"] = pd.to_numeric(df["Extended Cost"], errors="coerce").fillna(0)
            
    elif tipo == "wclog":
        # Workcenter Logs usa "Date" y "Time" con formato M/D/YYYY y H:MM AM/PM
        if "Date" in df.columns and "Time" in df.columns:
            # Combinar fecha y hora
            fecha_hora_str = df["Date"].astype(str) + " " + df["Time"].astype(str)
            # Intentar parsear con formato flexible
            df["timestamp"] = pd.to_datetime(fecha_hora_str, errors="coerce", infer_datetime_format=True)
            
            # Si hay NaT, intentar formato específico M/D/YYYY H:MM AM/PM
            mask_nat = df["timestamp"].isna()
            if mask_nat.any():
                df.loc[mask_nat, "timestamp"] = pd.to_datetime(
                    fecha_hora_str[mask_nat], 
                    format="%m/%d/%Y %I:%M %p",
                    errors="coerce"
                )
        # Ya tiene "Workcenter"
        if "Workcenter" in df.columns:
            df["workcenter"] = df["Workcenter"].astype(str).str.strip()
    
    # Crear columna de fecha
    if "timestamp" in df.columns:
        df["fecha"] = df["timestamp"].dt.date
    
    # Crear columna de hora
    if "timestamp" in df.columns:
        df["hora"] = df["timestamp"].dt.hour
    
    return df


def calcular_meta_por_hora(fecha: datetime.date, turno: str, rate_objetivo: float) -> pd.DataFrame:
    """
    Calcula la meta de producción por hora para el turno seleccionado.
    Considera turnos que cruzan medianoche.
    
    Args:
        fecha: Fecha del turno (fecha de inicio)
        turno: Código del turno
        rate_objetivo: Piezas por hora objetivo
    
    Returns:
        DataFrame con columnas 'hora' y 'meta'
    """
    info = SHIFTS[turno]
    start_t = info["start"]
    end_t = info["end"]
    
    horas = []
    metas = []
    
    # Si el turno cruza medianoche
    if start_t > end_t:
        # Desde start_t hasta 23:59 (mismo día)
        for h in range(start_t.hour, 24):
            horas.append(h)
            metas.append(rate_objetivo)
        # Desde 00:00 hasta end_t (día siguiente)
        for h in range(0, end_t.hour):
            horas.append(h)
            metas.append(rate_objetivo)
    else:
        # Turno normal dentro del mismo día
        for h in range(start_t.hour, end_t.hour):
            horas.append(h)
            metas.append(rate_objetivo)
    
    return pd.DataFrame({"hora": horas, "meta": metas})


# ====================================================
# CARGA Y PREPARACIÓN DE DATOS
# ====================================================

try:
    # Usar Google Drive para producción
    df_prod_raw = load_csv_from_drive(PROD_FILE_ID)
    df_scrap_raw = load_csv_from_drive(SCRAP_FILE_ID)
    df_wclog_raw = load_csv_from_drive(WCLOG_FILE_ID)
    df_costs_raw = load_csv_from_drive(COSTS_FILE_ID)
    
    # Para usar archivos locales en desarrollo, descomenta estas líneas y comenta las de arriba:
    # df_prod_raw = load_csv_local("Henniges Gomez Palacio 2 Production History Details-2025-11-13T193014.csv")
    # df_scrap_raw = load_csv_local("Henniges Gomez Palacio 2 Scrap Logs-2025-11-13T192931.csv")
    # df_wclog_raw = load_csv_local("Henniges Gomez Palacio 2 Workcenter Logs-2025-11-13T193145.csv")
    # df_costs_raw = load_csv_local("Henniges Gomez Palacio 2 Cost Structure-2025-11-13T201310.csv")
    
    # Preparar datos
    df_prod = preparar_datos(df_prod_raw, "prod")
    df_scrap = preparar_datos(df_scrap_raw, "scrap")
    df_wclog = preparar_datos(df_wclog_raw, "wclog")
    
    # NO localizar timezone aquí porque los datos YA están en hora de México
    # Solo necesitamos que datetime.now() use la timezone correcta para comparaciones
    
    # Preparar costs: sumar costo total por Part Number
    df_costs_raw.columns = df_costs_raw.columns.str.strip()
    df_costs_raw["Cost"] = pd.to_numeric(df_costs_raw["Cost"], errors="coerce").fillna(0)
    
    # Agrupar por Description (Part Number) y sumar todos los costos
    df_costs = df_costs_raw.groupby("Description")["Cost"].sum().reset_index()
    df_costs.columns = ["Part", "Total_Cost"]
    
    # Crear diccionario para búsqueda rápida
    cost_dict = dict(zip(df_costs["Part"], df_costs["Total_Cost"]))
    
    # Obtener lista de workcenters disponibles
    workcenters_disponibles = sorted(df_prod["workcenter"].dropna().unique().tolist())
    
    datos_cargados = True

except Exception as e:
    st.error(f"⚠️ Error al cargar los datos: {str(e)}")
    st.info("Por favor, verifica que los IDs de Google Drive sean correctos y que los archivos sean accesibles.")
    datos_cargados = False

# ====================================================
# LEER QUERY PARAMETERS PARA PERSISTIR CONFIGURACIÓN
# ====================================================
query_params = st.query_params

# ====================================================
# SIDEBAR - FILTROS
# ====================================================

st.sidebar.title("🔧 Filtros")

if datos_cargados:
    # Filtro de fecha
    fechas_disponibles = sorted(df_prod["fecha"].dropna().unique())
    if len(fechas_disponibles) > 0:
        # Mostrar rango de fechas disponibles para debug
        fecha_min_datos = min(fechas_disponibles)
        fecha_max_datos = max(fechas_disponibles)
        
        # Usar query param si existe, sino usar el máximo
        if "fecha" in query_params:
            try:
                fecha_default = datetime.strptime(query_params["fecha"], "%Y-%m-%d").date()
            except:
                fecha_default = fecha_max_datos
        else:
            fecha_default = fecha_max_datos
        
        fecha_sel = st.sidebar.date_input(
            "📅 Seleccionar Fecha",
            value=fecha_default,
            min_value=fecha_min_datos,
            max_value=fecha_max_datos,
            key="fecha_input"
        )
        
        # Info de fechas disponibles
        st.sidebar.caption(f"Datos desde {fecha_min_datos} hasta {fecha_max_datos}")
    else:
        st.sidebar.warning("No hay fechas disponibles en los datos.")
        fecha_sel = datetime.now().date()
    
    # Filtro de workcenters
    # Usar query param si existe
    if "wc" in query_params:
        wc_default = query_params["wc"].split(",") if query_params["wc"] else []
        # Filtrar solo los que existen
        wc_default = [wc for wc in wc_default if wc in workcenters_disponibles]
    else:
        wc_default = workcenters_disponibles[:config.DEFAULT_MAX_WORKCENTERS] if len(workcenters_disponibles) > 0 else []
    
    wc_sel = st.sidebar.multiselect(
        "🏭 Seleccionar Workcenters",
        options=workcenters_disponibles,
        default=wc_default,
        key="wc_input"
    )
    
    # Filtro de turno
    turno_opciones = {
        "A": "A (07:30 - 17:06)",
        "A + TE": "A + TE (07:30 - 19:30)",
        "C": "C (23:00 - 07:30)",
        "C + TE": "C + TE (19:30 - 07:30)",
        "1": "1 (07:30 - 15:30)",
        "2": "2 (15:30 - 23:00)"
    }
    
    # Usar query param si existe
    if "turno" in query_params and query_params["turno"] in turno_opciones:
        turno_default = query_params["turno"]
    else:
        turno_default = "A"
    
    # Obtener el índice del turno default
    turno_default_display = turno_opciones[turno_default]
    indice_turno = list(turno_opciones.values()).index(turno_default_display)
    
    turno_sel_display = st.sidebar.selectbox(
        "⏰ Seleccionar Turno",
        options=list(turno_opciones.values()),
        index=indice_turno,
        key="turno_input"
    )
    # Extraer el turno completo (A, A + TE, C, C + TE, 1, 2)
    for key, value in turno_opciones.items():
        if value == turno_sel_display:
            turno_sel = key
            break
    
    st.sidebar.markdown("---")
    
    # Configuración de supervisor
    es_supervisor = st.sidebar.checkbox("👤 Soy supervisor", value=False)
    
    # Usar query param para rate si existe
    if "rate" in query_params:
        try:
            rate_default = int(query_params["rate"])
        except:
            rate_default = config.DEFAULT_RATE
    else:
        rate_default = config.DEFAULT_RATE
    
    if es_supervisor:
        rate_objetivo = st.sidebar.number_input(
            "🎯 Rate Objetivo (pzas/hora)",
            min_value=1,
            max_value=1000,
            value=rate_default,
            step=1,
            help="Define el rate de producción objetivo en piezas por hora"
        )
    else:
        rate_objetivo = rate_default
        st.sidebar.info(f"📊 Rate objetivo: {rate_objetivo} pzas/hora")
    
    st.sidebar.markdown("---")
    
    # Botón para aplicar configuración y activar auto-refresh
    if st.sidebar.button("✅ Aplicar y Activar Auto-Refresh", use_container_width=True, type="primary"):
        # Actualizar query parameters con la configuración actual
        st.query_params.update({
            "fecha": fecha_sel.strftime("%Y-%m-%d"),
            "wc": ",".join(wc_sel),
            "turno": turno_sel,
            "rate": str(rate_objetivo)
        })
        st.rerun()
    
    # Botón para forzar recarga manual
    if st.sidebar.button("🔄 Recargar Datos Ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Mostrar si auto-refresh está activo
    if "wc" in query_params and query_params["wc"]:
        st.sidebar.success("✅ Auto-refresh ACTIVO")
        # Agregar meta refresh solo si la configuración está guardada
        st.markdown(
            f"""
            <meta http-equiv="refresh" content="{config.CACHE_TTL}">
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.warning("⚠️ Auto-refresh INACTIVO\nPresiona 'Aplicar y Activar' para comenzar")
    
    # Indicador de última actualización
    hora_actual = datetime.now().strftime("%I:%M:%S %p")
    
    st.sidebar.caption(f"🕐 Hora actual: {hora_actual}")
    if "wc" in query_params and query_params["wc"]:
        st.sidebar.caption(f"🔄 Recarga automática cada {config.CACHE_TTL}s")

else:
    st.sidebar.warning("⚠️ Datos no disponibles")
    fecha_sel = datetime.now().date()
    wc_sel = []
    turno_sel = "A"
    turno_sel_display = "A (07:30 - 17:06)"
    rate_objetivo = config.DEFAULT_RATE

# ====================================================
# TÍTULO PRINCIPAL
# ====================================================

st.markdown("<h3 style='text-align: center; margin: 0px; padding: 5px;'>🏭 Dashboard Henniges Automotive</h3>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; margin: 0px; padding: 0px; font-size: 14px;'>📅 {fecha_sel} | ⏰ {turno_sel_display} | 🏭 {', '.join(wc_sel[:2]) if wc_sel else 'N/A'}{' +' + str(len(wc_sel)-2) if len(wc_sel) > 2 else ''}</p>", unsafe_allow_html=True)

# ====================================================
# CÁLCULOS Y FILTRADO DE DATOS
# ====================================================

if datos_cargados and len(wc_sel) > 0:
    # Obtener info del turno para filtrar por horas
    info_turno = SHIFTS[turno_sel]
    start_t = info_turno["start"]
    end_t = info_turno["end"]
    
    # Determinar si el turno cruza medianoche
    turno_nocturno = start_t > end_t
    
    # Crear timestamps de inicio y fin del turno SIN timezone
    # Los datos CSV ya están en hora local de México, así que trabajamos todo en naive datetime
    start_dt = datetime.combine(fecha_sel, start_t)
    if turno_nocturno:
        end_dt = datetime.combine(fecha_sel + timedelta(days=1), end_t)
    else:
        end_dt = datetime.combine(fecha_sel, end_t)
    
    # Filtrar por rango de timestamp completo (más preciso que solo hora)
    df_prod_f = df_prod[
        (df_prod["workcenter"].isin(wc_sel)) &
        (df_prod["timestamp"] >= start_dt) &
        (df_prod["timestamp"] < end_dt)
    ].copy()
    
    df_scrap_f = df_scrap[
        (df_scrap["workcenter"].isin(wc_sel)) &
        (df_scrap["Department"].str.lower() == "acabados") &
        (df_scrap["timestamp"] >= start_dt) &
        (df_scrap["timestamp"] < end_dt)
    ].copy()
    
    df_wclog_f = df_wclog[
        (df_wclog["workcenter"].isin(wc_sel)) &
        (df_wclog["timestamp"] >= start_dt) &
        (df_wclog["timestamp"] < end_dt)
    ].copy()
    
    # Calcular tiempo muerto primero (necesario para análisis)
    df_wclog_calc = calcular_tiempo_muerto(df_wclog_f)
    
    # Calcular KPIs usando la hora local de México
    # Obtener la hora actual en la zona horaria de la planta
    tz = ZoneInfo(config.TIMEZONE)
    ahora_con_tz = datetime.now(tz)
    # Convertir a naive datetime (sin timezone) para comparar con los datos
    ahora = ahora_con_tz.replace(tzinfo=None)
    
    # Verificar si el turno ya terminó
    info_turno = SHIFTS[turno_sel]
    start_t = info_turno["start"]
    end_t = info_turno["end"]
    start_dt = datetime.combine(fecha_sel, start_t)
    
    if start_t > end_t:
        end_dt = datetime.combine(fecha_sel + timedelta(days=1), end_t)
    else:
        end_dt = datetime.combine(fecha_sel, end_t)
    
    # Si el turno ya terminó, usar la hora de fin en lugar de ahora
    tiempo_referencia = min(ahora, end_dt)
    turno_activo = ahora < end_dt and ahora >= start_dt
    
    horas_turno = horas_transcurridas_en_turno(fecha_sel, turno_sel, tiempo_referencia)
    meta_acumulada = rate_objetivo * horas_turno
    
    # Actualizar indicador de estado del turno
    if turno_activo:
        estado_turno = "🟢 EN VIVO"
        estado_color = "#2ecc71"
    else:
        if ahora < start_dt:
            estado_turno = "⏳ SIN INICIAR"
            estado_color = "#f39c12"
        else:
            estado_turno = "🔴 FINALIZADO"
            estado_color = "#e74c3c"
    
    st.markdown(f"<p style='text-align: center; color: {estado_color}; font-size: 16px; font-weight: bold; margin: 5px 0px;'>{estado_turno}</p>", unsafe_allow_html=True)
    
    # Producción real
    prod_real = df_prod_f["Prod"].fillna(0).sum() if "Prod" in df_prod_f.columns else 0
    
    # Calcular valor de producción en dólares
    if "Part" in df_prod_f.columns:
        df_prod_f["Part_Cost"] = df_prod_f["Part"].map(cost_dict).fillna(0)
        df_prod_f["Prod_Value"] = df_prod_f["Prod"] * df_prod_f["Part_Cost"]
        prod_value_dolares = df_prod_f["Prod_Value"].sum()
    else:
        prod_value_dolares = 0
    
    # Scrap (en dólares usando Extended Cost)
    if "Extended Cost" in df_scrap_f.columns:
        scrap_total_dolares = df_scrap_f["Extended Cost"].fillna(0).sum()
    else:
        scrap_total_dolares = 0
    
    scrap_cantidad = df_scrap_f["Scrap Qty"].fillna(0).sum() if "Scrap Qty" in df_scrap_f.columns else 0
    
    # Calcular % de scrap correctamente: Scrap $ / (Scrap $ + Producción $)
    total_value = scrap_total_dolares + prod_value_dolares
    scrap_porcentaje = (scrap_total_dolares / total_value * 100) if total_value > 0 else 0
    
    # Diferencia real vs meta
    diferencia = prod_real - meta_acumulada
    
    # Calcular performance (%)
    performance_pct = (prod_real / meta_acumulada * 100) if meta_acumulada > 0 else 0
    
    # Identificar paros NO programados y Tiempo Muerto para el KPI de downtime
    if "Status" in df_wclog_calc.columns:
        # Crear patrón regex para paradas programadas
        patron_programadas = "|".join(config.PARADAS_PROGRAMADAS_KEYWORDS)
        # Crear patrón regex para status corriendo
        patron_corriendo = "|".join(config.STATUS_CORRIENDO_KEYWORDS)
        
        # Tiempo Muerto incluye:
        # 1. Cualquier status que contenga "T.M." o "tiempo muerto"
        # 2. Paros NO programados (excluyendo corriendo y paradas programadas)
        df_tiempo_muerto = df_wclog_calc[
            (
                # Incluir explícitamente T.M. (Tiempo Muerto)
                df_wclog_calc["Status"].str.contains(r"T\.M\.", case=False, na=False, regex=True) |
                df_wclog_calc["Status"].str.lower().str.contains("tiempo muerto", case=False, na=False, regex=False)
            ) |
            (
                # O incluir paros que NO son corriendo NI paradas programadas
                ~df_wclog_calc["Status"].str.lower().str.contains(
                    patron_corriendo,
                    case=False,
                    na=False,
                    regex=True
                ) &
                ~df_wclog_calc["Status"].str.lower().str.contains(
                    patron_programadas,
                    case=False,
                    na=False,
                    regex=True
                )
            )
        ]
        tiempo_muerto_total = df_tiempo_muerto["duracion_min"].sum()
    else:
        tiempo_muerto_total = 0
    
    # ====================================================
    # DASHBOARD - KPIs PRINCIPALES
    # ====================================================
    
    # CSS para métricas más compactas
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] {
            font-size: 26px;
        }
        [data-testid="stMetricLabel"] {
            font-size: 14px;
        }
        [data-testid="stMetricDelta"] {
            font-size: 13px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            label="📦 Producción Real",
            value=f"{int(prod_real):,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="🎯 Meta Acumulada",
            value=f"{int(meta_acumulada):,}",
            delta=None
        )
    
    with col3:
        # Performance con color
        delta_performance = f"{performance_pct:.1f}%"
        if performance_pct >= 100:
            delta_sign = "normal"
        else:
            delta_sign = "inverse"
        
        st.metric(
            label="📊 Performance",
            value=delta_performance,
            delta="En meta" if performance_pct >= 100 else "Bajo meta",
            delta_color=delta_sign
        )
    
    with col4:
        st.metric(
            label="📊 Diferencia",
            value=f"{int(diferencia):,}",
            delta=f"{int(diferencia):,} pzas"
        )
    
    with col5:
        st.metric(
            label="💵 Scrap (USD)",
            value=f"${scrap_total_dolares:,.2f}",
            delta=f"{scrap_porcentaje:.2f}% del total"
        )
    
    with col6:
        st.metric(
            label="⏸️ Tiempo Muerto",
            value=f"{int(tiempo_muerto_total):,} min",
            delta=None
        )
    
    # ====================================================
    # LAYOUT EN DOS COLUMNAS
    # ====================================================
    
    col_izq, col_der = st.columns([3, 2])
    
    with col_izq:
        # ====================================================
        # GRÁFICA: PRODUCCIÓN REAL VS META POR HORA
        # ====================================================
        
        st.markdown("**📈 Producción Real vs Meta**")
        
        # Producción real por hora
        if "hora" in df_prod_f.columns and "Prod" in df_prod_f.columns:
            prod_por_hora = df_prod_f.groupby("hora")["Prod"].sum().reset_index()
            prod_por_hora.columns = ["hora", "produccion_real"]
        else:
            prod_por_hora = pd.DataFrame(columns=["hora", "produccion_real"])
        
        # Meta por hora
        meta_por_hora = calcular_meta_por_hora(fecha_sel, turno_sel, rate_objetivo)
        
        # Combinar ambos DataFrames
        if not prod_por_hora.empty and not meta_por_hora.empty:
            df_grafica = pd.merge(
                prod_por_hora,
                meta_por_hora,
                on="hora",
                how="outer"
            ).fillna(0).sort_values("hora")
            
            # Filtrar solo las horas del turno
            horas_turno_list = meta_por_hora["hora"].tolist()
            df_grafica = df_grafica[df_grafica["hora"].isin(horas_turno_list)]
            
            # Crear columna de hora formateada (HH:00)
            df_grafica["hora_formato"] = df_grafica["hora"].apply(lambda h: f"{int(h):02d}:00")
            
            # Crear lista ordenada de horas del turno para el eje X
            horas_turno_formato = [f"{int(h):02d}:00" for h in horas_turno_list]
            
            # Calcular el máximo del eje Y (al menos la meta máxima + 10%)
            max_meta = df_grafica["meta"].max()
            max_produccion = df_grafica["produccion_real"].max()
            max_y = max(max_meta, max_produccion) * 1.1
            
            # Crear gráfica base para producción real (línea azul)
            chart_prod = alt.Chart(df_grafica).mark_line(
                point=True, 
                color="#1f77b4",
                strokeWidth=2
            ).encode(
                x=alt.X("hora_formato:N", 
                        title="Hora", 
                        sort=horas_turno_formato,
                        axis=alt.Axis(labelAngle=-45),
                        scale=alt.Scale(domain=horas_turno_formato)),
                y=alt.Y("produccion_real:Q", title="Piezas", scale=alt.Scale(domain=[0, max_y])),
                tooltip=[
                    alt.Tooltip("hora_formato:N", title="Hora"),
                    alt.Tooltip("produccion_real:Q", title="Producción Real", format=",")
                ]
            )
            
            # Crear gráfica para meta (línea roja punteada)
            chart_meta = alt.Chart(df_grafica).mark_line(
                strokeDash=[5, 5],  # Línea punteada
                color="#e74c3c",  # Rojo
                strokeWidth=2
            ).encode(
                x=alt.X("hora_formato:N", sort=horas_turno_formato, scale=alt.Scale(domain=horas_turno_formato)),
                y=alt.Y("meta:Q", scale=alt.Scale(domain=[0, max_y])),
                tooltip=[
                    alt.Tooltip("hora_formato:N", title="Hora"),
                    alt.Tooltip("meta:Q", title="Meta", format=",")
                ]
            )
            
            # Combinar ambas gráficas
            chart = (chart_prod + chart_meta).properties(
                height=250
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No hay suficientes datos para generar la gráfica.")
    
    with col_der:
        # ====================================================
        # GRÁFICAS DE SCRAP
        # ====================================================
        
        st.markdown("**💵 Scrap Top 3**")
        
        if not df_scrap_f.empty and "Scrap Reason" in df_scrap_f.columns and "Extended Cost" in df_scrap_f.columns:
            # Top 3 razones de scrap por costo
            scrap_por_razon = df_scrap_f.groupby("Scrap Reason")["Extended Cost"].sum().reset_index()
            scrap_por_razon = scrap_por_razon.sort_values("Extended Cost", ascending=False).head(3)
            scrap_por_razon.columns = ["Razón", "Costo"]
            
            # Gráfica de barras verticales
            chart_scrap = alt.Chart(scrap_por_razon).mark_bar().encode(
                x=alt.X("Razón:N", title="Razón de Scrap", sort="-y", axis=alt.Axis(labelAngle=-45, labelLimit=100)),
                y=alt.Y("Costo:Q", title="Costo (USD)", axis=alt.Axis(format="$,.0f")),
                color=alt.Color("Costo:Q", scale=alt.Scale(scheme="reds"), legend=None),
                tooltip=[
                    alt.Tooltip("Razón:N", title="Razón"),
                    alt.Tooltip("Costo:Q", title="Costo (USD)", format="$,.2f")
                ]
            ).properties(
                height=250
            )
            
            st.altair_chart(chart_scrap, use_container_width=True)
        else:
            st.info("No hay datos de scrap disponibles.")
    
    # ====================================================
    # GRÁFICA: TIMELINE DE STATUS (COMPACTO)
    # ====================================================
    
    st.markdown("**⏱️ Timeline de Status por Workcenter**")
    
    if not df_wclog_calc.empty and "Status" in df_wclog_calc.columns:
        # Preparar datos para la gráfica de timeline (NO filtrar por duración para incluir status actual)
        df_timeline = df_wclog_calc.copy()
        
        if not df_timeline.empty:
            # Crear patrón regex para identificar paradas programadas
            patron = "|".join(config.PARADAS_PROGRAMADAS_KEYWORDS)
            
            # Clasificar cada status con más detalle (colores e iconos)
            def clasificar_status_detallado(status):
                status_lower = str(status).lower()
                
                # Producción (Verde)
                if any(keyword in status_lower for keyword in ["producción", "production", "corriendo", "running"]):
                    return {"tipo": "🟢 Producción", "color": "#2ecc71", "orden": 1}
                
                # Arranque (Verde claro)
                elif "arranque" in status_lower or "idle" in status_lower:
                    return {"tipo": "🟢 Arranque/Idle", "color": "#27ae60", "orden": 2}
                
                # Paradas Programadas (Amarillo/Naranja)
                elif "comida" in status_lower or "lunch" in status_lower:
                    return {"tipo": "🟡 Comida", "color": "#f39c12", "orden": 3}
                elif "break" in status_lower or "clockout" in status_lower:
                    return {"tipo": "🟡 Break", "color": "#e67e22", "orden": 4}
                elif "cambio" in status_lower and "modelo" in status_lower:
                    return {"tipo": "🟡 Cambio Modelo", "color": "#f39c12", "orden": 5}
                elif "preventivo" in status_lower:
                    return {"tipo": "🔧 Mtto Preventivo", "color": "#3498db", "orden": 6}
                
                # Mantenimiento Correctivo (Rojo)
                elif "correctivo" in status_lower:
                    if "molde" in status_lower:
                        return {"tipo": "🔴 Correctivo Molde", "color": "#e74c3c", "orden": 7}
                    elif "prensa" in status_lower:
                        return {"tipo": "🔴 Correctivo Prensa", "color": "#c0392b", "orden": 8}
                    elif "extrusión" in status_lower or "extrusion" in status_lower:
                        return {"tipo": "🔴 Correctivo Extrusión", "color": "#e74c3c", "orden": 9}
                    else:
                        return {"tipo": "🔴 Correctivo Equipo", "color": "#e74c3c", "orden": 10}
                
                # Tiempos Muertos específicos (Rojo oscuro)
                elif "falta" in status_lower and "material" in status_lower:
                    return {"tipo": "⛔ Falta Material", "color": "#8e44ad", "orden": 11}
                elif "calidad" in status_lower:
                    return {"tipo": "⚠️ T.M. Calidad", "color": "#e67e22", "orden": 12}
                elif "servicios" in status_lower:
                    return {"tipo": "⚡ Falla Servicios", "color": "#c0392b", "orden": 13}
                elif "dados" in status_lower:
                    return {"tipo": "🔧 Dados", "color": "#e74c3c", "orden": 14}
                
                # Apagado (Gris)
                elif "apagado" in status_lower:
                    return {"tipo": "⚫ Apagado", "color": "#95a5a6", "orden": 15}
                
                # Otros paros no programados (Rojo)
                else:
                    return {"tipo": "🔴 Paro No Programado", "color": "#e74c3c", "orden": 16}
            
            df_timeline["status_clasificado"] = df_timeline["Status"].apply(clasificar_status_detallado)
            df_timeline["tipo_status"] = df_timeline["status_clasificado"].apply(lambda x: x["tipo"])
            df_timeline["color_status"] = df_timeline["status_clasificado"].apply(lambda x: x["color"])
            df_timeline["orden_status"] = df_timeline["status_clasificado"].apply(lambda x: x["orden"])
            
            # Ordenar por workcenter y timestamp (ya tienen timezone de la carga inicial)
            df_timeline = df_timeline.sort_values(["workcenter", "timestamp"]).reset_index(drop=True)
            
            # Crear timestamps de inicio y fin para cada registro
            # Si el primer registro de un workcenter es después del inicio del turno, agregar un registro inicial
            registros_expandidos = []
            
            for wc in df_timeline["workcenter"].unique():
                df_wc = df_timeline[df_timeline["workcenter"] == wc].copy()
                
                # Inicio del turno para este workcenter
                inicio_turno_wc = start_dt
                
                for idx, row in df_wc.iterrows():
                    ts_inicio = row["timestamp"]
                    
                    # Si hay gap entre inicio de turno y primer registro, agregar estado "Apagado"
                    if idx == df_wc.index[0] and ts_inicio > inicio_turno_wc:
                        registros_expandidos.append({
                            "workcenter": wc,
                            "timestamp_inicio": inicio_turno_wc,
                            "timestamp_fin": ts_inicio,
                            "tipo_status": "Paro No Programado",
                            "Status": "Apagado (inicio)",
                            "duracion_min": (ts_inicio - inicio_turno_wc).total_seconds() / 60
                        })
                    
                    # Calcular timestamp de fin
                    if idx < df_wc.index[-1]:
                        # Hay un siguiente registro, usar su timestamp
                        siguiente_idx = df_wc.index[df_wc.index.get_loc(idx) + 1]
                        ts_fin = df_wc.loc[siguiente_idx, "timestamp"]
                    else:
                        # Es el último registro, extender hasta ahora (si estamos en el turno)
                        # o hasta el fin del turno (si el turno ya terminó)
                        # Obtener hora actual de México como naive datetime
                        tz = ZoneInfo(config.TIMEZONE)
                        ahora = datetime.now(tz).replace(tzinfo=None)
                        if ahora < end_dt:
                            # Turno aún activo, mostrar hasta ahora
                            ts_fin = ahora
                        else:
                            # Turno ya terminó, usar fin de turno
                            ts_fin = end_dt
                    
                    # Aplicar límite de 30 min para paradas programadas
                    duracion_original = (ts_fin - ts_inicio).total_seconds() / 60
                    
                    if row["tipo_status"] == "Parada Programada" and duracion_original > 30:
                        # Dividir: 30 min programado + exceso no programado
                        ts_fin_programado = ts_inicio + timedelta(minutes=30)
                        registros_expandidos.append({
                            "workcenter": wc,
                            "timestamp_inicio": ts_inicio,
                            "timestamp_fin": ts_fin_programado,
                            "tipo_status": "Parada Programada",
                            "Status": row["Status"],
                            "duracion_min": 30
                        })
                        registros_expandidos.append({
                            "workcenter": wc,
                            "timestamp_inicio": ts_fin_programado,
                            "timestamp_fin": ts_fin,
                            "tipo_status": "Paro No Programado",
                            "Status": f"{row['Status']} (exceso)",
                            "duracion_min": duracion_original - 30
                        })
                    else:
                        registros_expandidos.append({
                            "workcenter": wc,
                            "timestamp_inicio": ts_inicio,
                            "timestamp_fin": ts_fin,
                            "tipo_status": row["tipo_status"],
                            "Status": row["Status"],
                            "duracion_min": duracion_original
                        })
            
            df_gantt = pd.DataFrame(registros_expandidos)
            
            if not df_gantt.empty:
                # Aplicar clasificación detallada a los registros expandidos
                def clasificar_status_detallado_gantt(status):
                    status_lower = str(status).lower()
                    
                    # Producción (Verde)
                    if any(keyword in status_lower for keyword in ["producción", "production", "corriendo", "running"]):
                        return "🟢 Producción"
                    
                    # Arranque (Verde claro)
                    elif "arranque" in status_lower or "idle" in status_lower:
                        return "🟢 Arranque/Idle"
                    
                    # Paradas Programadas (Amarillo/Naranja)
                    elif "comida" in status_lower or "lunch" in status_lower:
                        return "🟡 Comida"
                    elif "break" in status_lower or "clockout" in status_lower:
                        return "🟡 Break"
                    elif "cambio" in status_lower and "modelo" in status_lower:
                        return "🟡 Cambio Modelo"
                    elif "preventivo" in status_lower:
                        return "🔧 Mtto Preventivo"
                    
                    # Mantenimiento Correctivo (Rojo)
                    elif "correctivo" in status_lower:
                        if "molde" in status_lower:
                            return "🔴 Correctivo Molde"
                        elif "prensa" in status_lower:
                            return "🔴 Correctivo Prensa"
                        elif "extrusión" in status_lower or "extrusion" in status_lower:
                            return "🔴 Correctivo Extrusión"
                        else:
                            return "🔴 Correctivo Equipo"
                    
                    # Tiempos Muertos específicos
                    elif "falta" in status_lower and "material" in status_lower:
                        return "⛔ Falta Material"
                    elif "calidad" in status_lower:
                        return "⚠️ T.M. Calidad"
                    elif "servicios" in status_lower:
                        return "⚡ Falla Servicios"
                    elif "dados" in status_lower:
                        return "🔧 Dados"
                    
                    # Apagado (Gris)
                    elif "apagado" in status_lower:
                        return "⚫ Apagado"
                    
                    # Otros paros no programados (Rojo)
                    else:
                        return "🔴 Paro No Programado"
                
                df_gantt["tipo_status_detallado"] = df_gantt["Status"].apply(clasificar_status_detallado_gantt)
                
                # Formatear timestamps para tooltip
                df_gantt["hora_inicio_formato"] = df_gantt["timestamp_inicio"].dt.strftime("%H:%M")
                df_gantt["hora_fin_formato"] = df_gantt["timestamp_fin"].dt.strftime("%H:%M")
                
                # Obtener solo las categorías que están presentes en los datos
                categorias_presentes = df_gantt["tipo_status_detallado"].unique().tolist()
                
                # Mapeo completo de categorías a colores
                mapeo_colores = {
                    "🟢 Producción": "#2ecc71",
                    "🟢 Arranque/Idle": "#27ae60",
                    "🟡 Comida": "#f39c12",
                    "🟡 Break": "#e67e22",
                    "🟡 Cambio Modelo": "#f39c12",
                    "🔧 Mtto Preventivo": "#3498db",
                    "🔧 Dados": "#e74c3c",
                    "🔴 Correctivo Molde": "#e74c3c",
                    "🔴 Correctivo Prensa": "#c0392b",
                    "🔴 Correctivo Extrusión": "#e74c3c",
                    "🔴 Correctivo Equipo": "#e74c3c",
                    "⛔ Falta Material": "#8e44ad",
                    "⚠️ T.M. Calidad": "#e67e22",
                    "⚡ Falla Servicios": "#c0392b",
                    "⚫ Apagado": "#95a5a6",
                    "🔴 Paro No Programado": "#e74c3c"
                }
                
                # Filtrar solo los colores de las categorías presentes
                colores_presentes = [mapeo_colores[cat] for cat in categorias_presentes if cat in mapeo_colores]
                
                # Crear gráfica de barras (Gantt chart) con timestamps reales en eje X
                chart_timeline = alt.Chart(df_gantt).mark_bar(size=30).encode(
                    x=alt.X("timestamp_inicio:T", 
                            title="Hora del Turno", 
                            axis=alt.Axis(format="%H:%M", labelAngle=-45)),
                    x2="timestamp_fin:T",
                    y=alt.Y("workcenter:N", title="", axis=alt.Axis(labelLimit=150)),
                    color=alt.Color(
                        "tipo_status_detallado:N",
                        title="Status",
                        scale=alt.Scale(
                            domain=categorias_presentes,
                            range=colores_presentes
                        ),
                        legend=alt.Legend(labelLimit=200, symbolLimit=20, columns=1)
                    ),
                    tooltip=[
                        alt.Tooltip("workcenter:N", title="Workcenter"),
                        alt.Tooltip("Status:N", title="Status"),
                        alt.Tooltip("tipo_status_detallado:N", title="Categoría"),
                        alt.Tooltip("hora_inicio_formato:N", title="Inicio"),
                        alt.Tooltip("hora_fin_formato:N", title="Fin"),
                        alt.Tooltip("duracion_min:Q", title="Duración (min)", format=".1f")
                    ]
                ).properties(
                    height=max(150, min(300, len(df_gantt["workcenter"].unique()) * 40))
                )
                
                st.altair_chart(chart_timeline, use_container_width=True)
        else:
            st.info("No hay registros de status con duración suficiente para mostrar.")
    else:
        st.info("No hay datos de workcenter logs para generar el timeline.")

elif datos_cargados and len(wc_sel) == 0:
    st.warning("⚠️ Por favor, selecciona al menos un Workcenter en el panel lateral.")

else:
    st.error("⚠️ No se pudieron cargar los datos. Verifica la configuración.")
