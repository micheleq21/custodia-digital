import streamlit as st
import pandas as pd
import os
import string
import zipfile
import io
from datetime import datetime

# Importaciones para Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# CONFIGURACIÓN DE RUTAS Y GOOGLE DRIVE
# ==========================================
DRIVE_FOLDER_ID = "1mWmUetoNl4wBaE6b1ZFDPh9v9ovJGFvk"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
BASE_DATOS_DIR = os.path.join(ROOT_DIR, "2_BASE_DATOS")
SECUENCIAS_DIR = os.path.join(BASE_DATOS_DIR, "secuencias")
EXCEL_PATH = os.path.join(BASE_DATOS_DIR, "Registro_Secuencias_Fotograficas.xlsx")
USUARIOS_PATH = os.path.join(BASE_DATOS_DIR, "usuarios.csv")
CONFIG_PATH = os.path.join(BASE_DATOS_DIR, "configuracion.csv")
AVISOS_PATH = os.path.join(BASE_DATOS_DIR, "avisos.csv")
DESCARGAS_LOG_PATH = os.path.join(BASE_DATOS_DIR, "log_descargas.csv")

os.makedirs(SECUENCIAS_DIR, exist_ok=True)

st.set_page_config(
    page_title="Custodia Digital - Criminalística",
    page_icon="📷",
    layout="wide"
)

# ==========================================
# FUNCIONES DE GOOGLE DRIVE
# ==========================================
def get_drive_service():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def crear_subcarpeta_drive(service, nombre_carpeta, parent_id):
    file_metadata = {
        'name': nombre_carpeta,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def subir_foto_drive(service, file_bytes, nombre_foto, mime_type, folder_id):
    file_metadata = {
        'name': nombre_foto,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return file.get('webViewLink')

# ==========================================
# ESTILOS CSS PROFESIONALES (AZUL MARINO INSTITUCIONAL)
# ==========================================
st.markdown("""
    <style>
    /* Estilos Generales */
    .stApp {
        background-color: #F4F6F9;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #001A33 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    
    /* Títulos Principales */
    h1 {
        color: #001F3F !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        border-bottom: 3px solid #002B49;
        padding-bottom: 10px;
        margin-bottom: 25px !important;
    }
    h2, h3 {
        color: #002B49 !important;
        font-weight: 600 !important;
    }

    /* Banners y Tarjetas Personalizadas */
    .banner-header {
        background: linear-gradient(135deg, #001F3F 0%, #003366 100%);
        color: white;
        padding: 20px 25px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        margin-bottom: 25px;
    }
    .banner-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: 0.5px;
    }
    .banner-subtitle {
        font-size: 14px;
        color: #D0E1F9;
        margin-top: 5px;
    }
    
    .card-info {
        background-color: #FFFFFF;
        border-left: 5px solid #003366;
        padding: 18px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 15px;
    }

    /* Botones */
    .stButton>button {
        background: linear-gradient(180deg, #002B49 0%, #001F3F 100%);
        color: #FFFFFF !important;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background: linear-gradient(180deg, #003366 0%, #002B49 100%);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        transform: translateY(-1px);
    }

    /* Contenedores de Formulario */
    [data-testid="stForm"] {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNCIONES DE MANEJO DE DATOS Y AUDITORÍA
# ==========================================
def cargar_configuracion():
    if not os.path.exists(CONFIG_PATH):
        df_cfg = pd.DataFrame([{"ultimo_numero_itf": 34}])
        df_cfg.to_csv(CONFIG_PATH, index=False)
        return df_cfg
    return pd.read_csv(CONFIG_PATH)

def guardar_configuracion(num_itf):
    df_cfg = pd.DataFrame([{"ultimo_numero_itf": int(num_itf)}])
    df_cfg.to_csv(CONFIG_PATH, index=False)

def cargar_usuarios():
    if not os.path.exists(USUARIOS_PATH):
        df_def = pd.DataFrame([
            {"usuario": "admin", "clave": "admin2026", "rol": "Administrador", "nombre": "Jefe de Gabinete"},
            {"usuario": "guardia", "clave": "guardia2026", "rol": "Efectivo", "nombre": "Guardia de Turno"}
        ])
        df_def.to_csv(USUARIOS_PATH, index=False)
        return df_def
    return pd.read_csv(USUARIOS_PATH, dtype=str)

def guardar_usuarios(df_users):
    df_users.to_csv(USUARIOS_PATH, index=False)

def cargar_avisos():
    if not os.path.exists(AVISOS_PATH):
        df_av = pd.DataFrame(columns=[
            "id_aviso", "destinatario", "mensaje", "fecha_emision", "estado", "leido_por", "fecha_lectura"
        ])
        df_av.to_csv(AVISOS_PATH, index=False)
        return df_av
    
    df_av = pd.read_csv(AVISOS_PATH, dtype=str)
    for col in ["destinatario", "mensaje", "estado", "leido_por", "fecha_lectura"]:
        if col in df_av.columns:
            df_av[col] = df_av[col].astype(str).fillna("")
            
    return df_av

def guardar_avisos(df_av):
    df_av.to_csv(AVISOS_PATH, index=False)

def registrar_descarga_log(nombre_carpeta, usuario, nombre_usuario):
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_log = pd.DataFrame([{
        "Fecha_Hora": ahora_str,
        "Nombre_Carpeta": nombre_carpeta,
        "Usuario": usuario,
        "Nombre_Usuario": nombre_usuario
    }])
    if os.path.exists(DESCARGAS_LOG_PATH):
        nuevo_log.to_csv(DESCARGAS_LOG_PATH, mode='a', header=False, index=False)
    else:
        nuevo_log.to_csv(DESCARGAS_LOG_PATH, index=False)

def cargar_log_descargas():
    if not os.path.exists(DESCARGAS_LOG_PATH):
        return pd.DataFrame(columns=["Fecha_Hora", "Nombre_Carpeta", "Usuario", "Nombre_Usuario"])
    return pd.read_csv(DESCARGAS_LOG_PATH, dtype=str)

def generar_letra_secuencia(numero_hecho_mes):
    letras = string.ascii_uppercase
    indice = (numero_hecho_mes - 1) % 26
    ciclo = (numero_hecho_mes - 1) // 26
    letra_base = letras[indice]
    return letra_base if ciclo == 0 else f"{letra_base}.{ciclo}"

def obtener_siguiente_secuencia():
    fecha_hoy = datetime.now()
    mes_actual = fecha_hoy.month
    anio_actual = fecha_hoy.year

    if not os.path.exists(EXCEL_PATH):
        return generar_letra_secuencia(1), 1

    try:
        df = pd.read_excel(EXCEL_PATH)
        if df.empty or 'Fecha_Carga' not in df.columns:
            return generar_letra_secuencia(1), 1
        
        df['Fecha_dt'] = pd.to_datetime(df['Fecha_Carga'], errors='coerce')
        mismo_mes = df[
            (df['Fecha_dt'].dt.month == mes_actual) & 
            (df['Fecha_dt'].dt.year == anio_actual)
        ]
        conteo_mes = len(mismo_mes) + 1
        return generar_letra_secuencia(conteo_mes), conteo_mes
    except Exception:
        return generar_letra_secuencia(1), 1

def obtener_siguiente_itf():
    df_cfg = cargar_configuracion()
    ultimo_num = int(df_cfg.iloc[0]['ultimo_numero_itf'])
    siguiente_num = ultimo_num + 1
    anio_actual = datetime.now().year
    formato_itf = f"N° {siguiente_num:03d}-SFP-DG.CRIM.LA/{anio_actual}"
    return formato_itf, siguiente_num

def guardar_registro_excel(datos_registro):
    nuevo_df = pd.DataFrame([datos_registro])
    if os.path.exists(EXCEL_PATH):
        try:
            df_existente = pd.read_excel(EXCEL_PATH)
            df_final = pd.concat([df_existente, nuevo_df], ignore_index=True)
        except Exception:
            df_final = nuevo_df
    else:
        df_final = nuevo_df

    df_final.to_excel(EXCEL_PATH, index=False)

def crear_zip_carpeta(ruta_carpeta):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(ruta_carpeta):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, ruta_carpeta)
                zip_file.write(filepath, arcname)
    buffer.seek(0)
    return buffer

# ==========================================
# INICIO DE SESIÓN
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_data" not in st.session_state:
    st.session_state["usuario_data"] = {}

df_usuarios = cargar_usuarios()

if not st.session_state["autenticado"]:
    st.markdown("""
        <div class="banner-header" style="text-align: center;">
            <div class="banner-title">🏛️ SISTEMA DE CUSTODIA DIGITAL</div>
            <div class="banner-subtitle">DIVISIÓN GABINETE CRIMINALÍSTICO LOS ANTIGUOS - POLICÍA DE LA PROVINCIA DE SANTA CRUZ</div>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        with st.form("form_login"):
            st.subheader("🔐 Autenticación de Usuario")
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Ingresar al Sistema")
            
            if btn_login:
                user_match = df_usuarios[(df_usuarios['usuario'] == user_input) & (df_usuarios['clave'] == pass_input)]
                if not user_match.empty:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_data"] = user_match.iloc[0].to_dict()
                    st.success(f"Bienvenido/a {st.session_state['usuario_data']['nombre']}")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()

# ==========================================
# ENCABEZADO Y NAVEGACIÓN
# ==========================================
u_data = st.session_state["usuario_data"]

st.markdown(f"""
    <div class="banner-header">
        <div class="banner-title">📷 SISTEMA DE CUSTODIA Y PRESERVACIÓN DIGITAL</div>
        <div class="banner-subtitle">División Gabinete Criminalístico Los Antiguos | Usuario Activo: <b>{u_data['nombre']}</b> ({u_data['rol']})</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("MENÚ PRINCIPAL")
st.sidebar.markdown("---")

if u_data['rol'] == "Administrador":
    opcion_menu = st.sidebar.radio(
        "Navegación",
        [
            "📝 Cargar Secuencia", 
            "🔍 Buscar y Descargar Hechos", 
            "📊 Panel Estadístico / Resumen", 
            "👥 Administración de Usuarios", 
            "⚙️ Configuración / Avisos e ITF",
            "🔑 Cambiar Mi Contraseña"
        ]
    )
else:
    opcion_menu = st.sidebar.radio(
        "Navegación",
        [
            "📝 Cargar Secuencia", 
            "🔍 Buscar y Descargar Hechos", 
            "🔑 Cambiar Mi Contraseña"
        ]
    )

st.sidebar.markdown("---")
if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_data"] = {}
    st.rerun()

df_config = cargar_configuracion()

# ==========================================
# 1. CARGAR SECUENCIA
# ==========================================
if opcion_menu == "📝 Cargar Secuencia":
    st.title("📝 Registro de Secuencias Fotográficas")
    
    # SECCIÓN DE NOTIFICACIONES DIRIGIDAS / GENERALES
    df_avisos = cargar_avisos()
    usuario_actual = str(u_data['usuario'])
    nombre_actual = str(u_data['nombre']).upper()
    
    avisos_pendientes = df_avisos[
        (df_avisos['estado'] == 'PENDIENTE') & 
        (
            (df_avisos['destinatario'] == 'GENERAL') | 
            (df_avisos['destinatario'].str.upper() == usuario_actual.upper()) |
            (df_avisos['destinatario'].str.upper().apply(lambda dest: dest in nombre_actual if dest else False))
        )
    ]
    
    if not avisos_pendientes.empty:
        st.warning("📢 **NOTIFICACIONES Y ÓRDENES PENDIENTES DE LA JEFATURA**")
        for idx, row in avisos_pendientes.iterrows():
            with st.container():
                st.markdown(f"**Fecha:** `{row['fecha_emision']}` | **Destino:** `{row['destinatario']}`")
                st.info(f"📌 {row['mensaje']}")
                
                if st.button(f"☑️ Marcar como Leído / Aceptado (Aviso ID {row['id_aviso']})", key=f"btn_aviso_{row['id_aviso']}"):
                    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    df_avisos['leido_por'] = df_avisos['leido_por'].astype(str)
                    df_avisos['fecha_lectura'] = df_avisos['fecha_lectura'].astype(str)
                    df_avisos['estado'] = df_avisos['estado'].astype(str)
                    
                    mask = df_avisos['id_aviso'].astype(str) == str(row['id_aviso'])
                    df_avisos.loc[mask, 'estado'] = 'LEIDO'
                    df_avisos.loc[mask, 'leido_por'] = str(u_data['nombre'])
                    df_avisos.loc[mask, 'fecha_lectura'] = ahora_str
                    
                    guardar_avisos(df_avisos)
                    st.success("✅ Notificación aceptada y registrada con éxito.")
                    st.rerun()
        st.markdown("---")

    letra_actual, num_hecho_mes = obtener_siguiente_secuencia()
    itf_formateado, num_itf_actual = obtener_siguiente_itf()
    
    c_info1, c_info2 = st.columns(2)
    with c_info1:
        st.markdown(f"""
            <div class="card-info">
                <div style="font-size: 13px; color: #555; font-weight: 600;">SECUENCIA MENSUAL ASIGNADA</div>
                <div style="font-size: 22px; color: #001F3F; font-weight: 700;">Secuencia: {letra_actual}</div>
                <div style="font-size: 12px; color: #777;">(Corresponde al hecho N° {num_hecho_mes} del mes actual)</div>
            </div>
        """, unsafe_allow_html=True)
    with c_info2:
        st.markdown(f"""
            <div class="card-info" style="border-left-color: #28A745;">
                <div style="font-size: 13px; color: #555; font-weight: 600;">INFORME TÉCNICO FOTOGRÁFICO (ITF)</div>
                <div style="font-size: 20px; color: #28A745; font-weight: 700;">{itf_formateado}</div>
                <div style="font-size: 12
