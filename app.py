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
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ==========================================
# CONFIGURACIÓN DE RUTAS Y GOOGLE DRIVE
# ==========================================
DRIVE_FOLDER_ID = "1mWmUetoNl4wBaE6b1ZFDPh9v9ovJGFvk"
CORREO_PROPIETARIO = "custodiadigital.criminalistica@gmail.com"

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
# FUNCIONES ROBUSTAS DE GOOGLE DRIVE
# ==========================================
def get_drive_service():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def crear_subcarpeta_drive(service, nombre_carpeta, parent_id):
    folder_id = None
    
    # 1. Intento primario: Crear dentro de la carpeta asignada
    try:
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(
            body=file_metadata, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        folder_id = folder.get('id')
    except Exception:
        # 2. Fallback: Crear en la raíz propia de la Service Account si falla la carpeta padre
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(
            body=file_metadata, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        folder_id = folder.get('id')

    # Compartir automáticamente la carpeta creada con tu correo personal
    if folder_id:
        try:
            user_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': CORREO_PROPIETARIO
            }
            service.permissions().create(
                fileId=folder_id,
                body=user_permission,
                fields='id',
                supportsAllDrives=True
            ).execute()
        except Exception:
            pass

    return folder_id

def subir_foto_drive(service, file_bytes, nombre_foto, mime_type, folder_id):
    file_metadata = {
        'name': nombre_foto,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    return file.get('webViewLink')

def buscar_id_subcarpeta_drive(service, nombre_carpeta, parent_id):
    # Búsqueda global por nombre exacto en Drive
    query = f"name = '{nombre_carpeta}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        results = service.files().list(
            q=query, 
            fields="files(id, name)", 
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
    except Exception:
        pass
    return None

def descargar_zip_desde_drive(service, subcarpeta_id, nombre_zip):
    query = f"'{subcarpeta_id}' in parents and trashed = false"
    results = service.files().list(
        q=query, 
        fields="files(id, name)", 
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    archivos = results.get('files', [])

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for archivo in archivos:
            request = service.files().get_media(fileId=archivo['id'])
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            zip_file.writestr(archivo['name'], file_buffer.getvalue())
            
    buffer.seek(0)
    return buffer

# ==========================================
# ESTILOS CSS PROFESIONALES
# ==========================================
st.markdown("""
    <style>
    .stApp {
        background-color: #F4F6F9;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #001A33 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    h1 {
        color: #001F3F !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #002B49;
        padding-bottom: 10px;
        margin-bottom: 25px !important;
    }
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
    }
    .banner-subtitle {
        font-size: 14px;
        color: #D0E1F9;
        margin-top: 5px;
    }
    .stButton>button {
        background: linear-gradient(180deg, #002B49 0%, #001F3F 100%);
        color: #FFFFFF !important;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
    }
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
# MANEJO DE DATOS Y AUDITORÍA
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

def crear_zip_carpeta_local(ruta_carpeta):
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
            <div class="banner-subtitle">DIVISIÓN GABINETE CRIMINALÍSTICO LOS ANTIGUOS - POLICÍA DE SANTA CRUZ</div>
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

st.markdown("### 📷 SISTEMA DE CUSTODIA Y PRESERVACIÓN DIGITAL")
st.caption(f"División Gabinete Criminalístico Los Antiguos | Usuario Activo: **{u_data['nombre']}** ({u_data['rol']})")

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
        st.info(f"**SECUENCIA MENSUAL ASIGNADA:** {letra_actual} (Hecho N° {num_hecho_mes} del mes)")
    with c_info2:
        st.success(f"**INFORME TÉCNICO FOTOGRÁFICO (ITF):** {itf_formateado}")

    with st.form("form_carga_completo", clear_on_submit=True):
        st.subheader("1. Datos Generales de la Intervención")
        c1, c2, c3 = st.columns(3)
        with c1:
            lugar_hecho = st.text_input("Lugar del Hecho / Dirección *", placeholder="Ej: Av. San Martín 450")
            hora_hecho_manual = st.text_input("Hora del Hecho (Manual) *", placeholder="Ej: 04:30 hs", value=datetime.now().strftime("%H:%M"))
        with c2:
            sumario = st.text_input("N° de Causa / Sumario (Opcional)", placeholder="S/D (Si aún no se posee)")
            tipo_hecho = st.text_input("Carátula / Tipo de Hecho (Opcional)", placeholder="Ej: INVESTIGACION / S_D")
        with c3:
            camara_utilizada = st.selectbox("Cámara / Equipo Utilizado *", ["Nikon", "Canon", "Sony", "Teléfono Móvil Institucional", "Otra"])
            descripcion_hecho = st.text_area("Descripción / Observaciones", placeholder="Detalles preliminares del lugar...")

        st.subheader("2. Personal Interviniente")
        p1, p2, p3 = st.columns(3)
        with p1:
            perito_criminalistica = st.text_input("Oficial de Criminalística (Perito) *", value=u_data['nombre'])
        with p2:
            fotografo = st.text_input("Fotógrafo / Operador de Cámara *", placeholder="Nombre y Jerarquía")
        with p3:
            oficial_comisaria = st.text_input("Oficial de Comisaría Preventora", placeholder="Nombre y Jerarquía")

        st.subheader("3. Registro Fotográfico")
        m1, m2 = st.columns([1, 2])
        with m1:
            cant_fotos_manual = st.number_input("Cantidad de Fotos Sacadas *", min_value=1, value=1, step=1)
        with m2:
            archivos_fotos = st.file_uploader(
                "Cargar Fotografías de la Secuencia", 
                type=["jpg", "jpeg", "png"], 
                accept_multiple_files=True
            )

        enviado = st.form_submit_button("💾 Guardar y Registrar Secuencia")

    if enviado:
        if not lugar_hecho or not hora_hecho_manual or not perito_criminalistica or not fotografo:
            st.error("⚠️ Por favor completá los campos obligatorios (*).")
        elif not archivos_fotos:
            st.error("⚠️ Debes adjuntar al menos una fotografía.")
        else:
            ahora = datetime.now()
            fecha_str = ahora.strftime("%Y-%m-%d")
            hora_carga_str = ahora.strftime("%H:%M:%S")
            prefijo_fecha = ahora.strftime("%Y_%m_%d")
            
            sumario_val = sumario.strip() if sumario.strip() else "SIN_SUMARIO"
            hecho_val = tipo_hecho.strip().upper() if tipo_hecho.strip() else "HECHO"
            
            sumario_limpio = sumario_val.replace("/", "_").replace(" ", "_")
            hecho_limpio = hecho_val.replace(" ", "_")
            
            nombre_carpeta = f"{prefijo_fecha}_SEC_{letra_actual}_SUM_{sumario_limpio}_{hecho_limpio}"
            ruta_carpeta = os.path.join(SECUENCIAS_DIR, nombre_carpeta)
            os.makedirs(ruta_carpeta, exist_ok=True)

            cant_fotos_subidas = len(archivos_fotos)

            drive_exito = False
            try:
                service = get_drive_service()
                subcarpeta_id = crear_subcarpeta_drive(service, nombre_carpeta, DRIVE_FOLDER_ID)
                
                if subcarpeta_id:
                    for idx, foto in enumerate(archivos_fotos, start=1):
                        ext = os.path.splitext(foto.name)[1]
                        nombre_foto = f"FOTO_{idx:03d}_{letra_actual}{ext}"
                        foto_bytes = foto.getbuffer()
                        
                        with open(os.path.join(ruta_carpeta, nombre_foto), "wb") as f:
                            f.write(foto_bytes)
                        
                        mime = "image/jpeg" if ext.lower() in [".jpg", ".jpeg"] else "image/png"
                        subir_foto_drive(service, foto_bytes, nombre_foto, mime, subcarpeta_id)
                    
                    drive_exito = True
            except Exception as e:
                st.error(f"⚠️ Error al conectar con Google Drive: {e}")

            registro = {
                "Fecha_Carga": fecha_str,
                "Hora_Carga": hora_carga_str,
                "Hora_Hecho": hora_hecho_manual,
                "Secuencia_Letra": letra_actual,
                "Numero_ITF": itf_formateado,
                "Lugar_Hecho": lugar_hecho,
                "Sumario": sumario_val,
                "Carátula": hecho_val,
                "Descripción": descripcion_hecho,
                "Perito_Criminalistica": perito_criminalistica,
                "Fotógrafo": fotografo,
                "Oficial_Comisaria": oficial_comisaria,
                "Cámara": camara_utilizada,
                "Cantidad_Fotos_Sacadas": cant_fotos_manual,
                "Cantidad_Fotos_Subidas": cant_fotos_subidas,
                "Nombre_Carpeta": nombre_carpeta,
                "Cargado_Por": u_data['usuario']
            }
            guardar_registro_excel(registro)

            guardar_configuracion(num_itf_actual)

            st.success(f"✅ ¡Secuencia **{letra_actual}** registrada con éxito!")
            if drive_exito:
                st.info("☁️ **Resguardo permanente activado:** Las fotos se guardaron exitosamente en tu Google Drive.")
            st.write(f"📄 **Informe Fotográfico Asignado:** `{itf_formateado}`")
            st.write(f"📁 **Carpeta:** `{nombre_carpeta}`")
            st.write(f"📷 **Fotos indicadas:** {cant_fotos_manual} | **Fotos subidas:** {cant_fotos_subidas} unidades.")
            st.balloons()

# ==========================================
# 2. BUSCAR Y DESCARGAR HECHOS
# ==========================================
elif opcion_menu == "🔍 Buscar y Descargar Hechos":
    st.title("🔍 Consulta y Descarga de Actuaciones")
    
    if not os.path.exists(EXCEL_PATH):
        st.warning("Aún no hay registros cargados en el sistema.")
    else:
        df_excel = pd.read_excel(EXCEL_PATH)
        df_logs = cargar_log_descargas()
        
        busqueda = st.text_input("🔎 Buscar por ITF, Lugar, Perito, Fotógrafo, Sumario o Letra:", "")
        
        if busqueda:
            df_filtrado = df_excel[
                df_excel.astype(str).apply(lambda row: row.str.contains(busqueda, case=False).any(), axis=1)
            ]
        else:
            df_filtrado = df_excel

        if u_data['rol'] == "Administrador":
            if not df_logs.empty:
                conteo_descargas = df_logs['Nombre_Carpeta'].value_counts().to_dict()
                df_filtrado['Total_Descargas'] = df_filtrado['Nombre_Carpeta'].map(conteo_descargas).fillna(0).astype(int)
            else:
                df_filtrado['Total_Descargas'] = 0

        st.dataframe(df_filtrado, use_container_width=True)

        st.markdown("---")
        st.subheader("📦 Descarga y Acceso a Material Fotográfico")
        
        carpetas_disponibles = df_filtrado['Nombre_Carpeta'].dropna().tolist()
        if carpetas_disponibles:
            carpeta_seleccionada = st.selectbox("Seleccionar Actuación / Hecho:", carpetas_disponibles)
            
            datos_hecho = df_excel[df_excel['Nombre_Carpeta'] == carpeta_seleccionada].iloc[0]
            
            usr_login = str(u_data['usuario']).strip().lower()
            usr_nombre = str(u_data['nombre']).strip().lower()
            usr_rol = u_data['rol']

            cargado_por = str(datos_hecho.get('Cargado_Por', '')).strip().lower()
            perito = str(datos_hecho.get('Perito_Criminalistica', '')).strip().lower()
            fotografo = str(datos_hecho.get('Fotógrafo', '')).strip().lower()

            es_interviniente = (
                usr_login == cargado_por or
                usr_login in perito or
                usr_login in fotografo or
                usr_nombre in perito or
                usr_nombre in fotografo
            )
            
            tiene_acceso = (usr_rol == "Administrador") or es_interviniente

            if usr_rol == "Administrador":
                cant_descargas = len(df_logs[df_logs['Nombre_Carpeta'] == carpeta_seleccionada]) if not df_logs.empty else 0
                st.info(f"📊 **INFORMACIÓN DE AUDITORÍA:** Esta carpeta ha sido descargada **{cant_descargas} veces** en total.")

            if tiene_acceso:
                st.success("✅ **ACCESO AUTORIZADO:** Usted figura como personal interviniente o autoridad supervisora en esta actuación.")
                
                zip_buffer = None
                ruta_completa_local = os.path.join(SECUENCIAS_DIR, carpeta_seleccionada)
                
                if os.path.exists(ruta_completa_local) and len(os.listdir(ruta_completa_local)) > 0:
                    zip_buffer = crear_zip_carpeta_local(ruta_completa_local)
                else:
                    try:
                        service = get_drive_service()
                        subcarpeta_id = buscar_id_subcarpeta_drive(service, carpeta_seleccionada, DRIVE_FOLDER_ID)
                        if subcarpeta_id:
                            zip_buffer = descargar_zip_desde_drive(service, subcarpeta_id, f"{carpeta_seleccionada}.zip")
                    except Exception as e:
                        st.error(f"Error al obtener archivos desde la nube: {e}")

                if zip_buffer:
                    st.download_button(
                        label=f"⬇️ Descargar Fotografías de `{carpeta_seleccionada}` (ZIP)",
                        data=zip_buffer,
                        file_name=f"{carpeta_seleccionada}.zip",
                        mime="application/zip",
                        on_click=registrar_descarga_log,
                        args=(carpeta_seleccionada, u_data['usuario'], u_data['nombre'])
                    )
                else:
                    st.warning("⚠️ No se encontraron archivos para esta secuencia en la nube ni en el servidor local.")
            else:
                st.error("🚫 **ACCESO DENEGADO — RESTRICCIÓN DE CUSTODIA DIGITAL**\n\nUsted no figura como personal interviniente en las presentes actuaciones.\n\n*Por razones de confidencialidad institucional, el acceso se encuentra reservado al personal participante y a la Jefatura del Gabinete.*")

# ==========================================
# 3. PANEL ESTADÍSTICO
# ==========================================
elif opcion_menu == "📊 Panel Estadístico / Resumen":
    st.title("📊 Estándares y Estadísticas Operativas")
    
    if not os.path.exists(EXCEL_PATH):
        st.warning("No hay datos cargados para generar estadísticas.")
    else:
        df_stats = pd.read_excel(EXCEL_PATH)
        df_stats['Fecha_dt'] = pd.to_datetime(df_stats['Fecha_Carga'], errors='coerce')
        df_logs = cargar_log_descargas()
        
        st.metric("Total de Actuaciones Registradas", len(df_stats))
        st.markdown("---")

        st.subheader("📈 Volumen de Intervenciones Mensuales")
        
        if not df_stats['Fecha_dt'].dropna().empty:
            df_stats['Año_Mes'] = df_stats['Fecha_dt'].dt.strftime('%Y-%m (%B)')
            col_cant = 'Cantidad_Fotos_Sacadas' if 'Cantidad_Fotos_Sacadas' in df_stats.columns else 'Cantidad_Fotos'
            
            conteo_meses = df_stats.groupby('Año_Mes').agg(
                Cantidad_Hechos=('Secuencia_Letra', 'count'),
                Total_Fotos=(col_cant, 'sum')
            ).reset_index()

            st.dataframe(conteo_meses, use_container_width=True)
            st.bar_chart(conteo_meses.set_index('Año_Mes')['Cantidad_Hechos'])
        else:
            st.info("No hay fechas válidas registradas para agrupar por mes.")

        st.markdown("---")
        st.subheader("🕵️‍♂️ Historial y Auditoría de Descargas de Fotografías")
        if df_logs.empty:
            st.info("Aún no se registran descargas de carpetas de evidencia.")
        else:
            st.dataframe(df_logs, use_container_width=True)

# ==========================================
# 4. ADMINISTRACIÓN DE USUARIOS
# ==========================================
elif opcion_menu == "👥 Administración de Usuarios":
    st.title("👥 Gestión de Personal y Accesos")
    
    st.subheader("Alta o Modificación de Personal")
    with st.form("form_usuario"):
        c1, c2 = st.columns(2)
        with c1:
            nuevo_user = st.text_input("Usuario (Ej: f_quiroga)")
            nuevo_nombre = st.text_input("Nombre, Apellido y Jerarquía")
        with c2:
            nueva_clave = st.text_input("Contraseña", type="password")
            nuevo_rol = st.selectbox("Rol Asignado", ["Efectivo", "Administrador"])
            
        btn_guardar_u = st.form_submit_button("💾 Guardar Datos del Usuario")

    if btn_guardar_u:
        if not nuevo_user or not nueva_clave or not nuevo_nombre:
            st.error("Todos los campos son obligatorios.")
        else:
            if nuevo_user in df_usuarios['usuario'].values:
                df_usuarios.loc[df_usuarios['usuario'] == nuevo_user, ['clave', 'rol', 'nombre']] = [nueva_clave, nuevo_rol, nuevo_nombre]
                st.success(f"Usuario `{nuevo_user}` actualizado correctamente.")
            else:
                nueva_fila = pd.DataFrame([{"usuario": nuevo_user, "clave": nueva_clave, "rol": nuevo_rol, "nombre": nuevo_nombre}])
                df_usuarios = pd.concat([df_usuarios, nueva_fila], ignore_index=True)
                st.success(f"Usuario `{nuevo_user}` creado con éxito.")
            
            guardar_usuarios(df_usuarios)
            st.rerun()

    st.markdown("---")
    st.subheader("Padrón de Usuarios Registrados")
    st.dataframe(df_usuarios[['usuario', 'nombre', 'rol', 'clave']], use_container_width=True)

# ==========================================
# 5. CONFIGURACIÓN DE AVISOS Y CONTADOR ITF
# ==========================================
elif opcion_menu == "⚙️ Configuración / Avisos e ITF":
    st.title("⚙️ Administración Institucional y Configuración")
    
    ultimo_itf_actual = int(df_config.iloc[0]['ultimo_numero_itf'])
    df_avisos = cargar_avisos()
    
    st.subheader("📢 1. Emisión de Notificaciones u Órdenes de Servicio")
    
    opciones_usuarios = ["GENERAL"] + df_usuarios['usuario'].tolist() + df_usuarios['nombre'].tolist()
    modo_destinatario = st.radio("Destinatario:", ["Seleccionar de la lista", "Ingresar manualmente"], horizontal=True)
    
    with st.form("form_nuevo_aviso"):
        c_av1, c_av2 = st.columns([1.5, 3])
        with c_av1:
            if modo_destinatario == "Seleccionar de la lista":
                destinatario_sel = st.selectbox("Destinatario *", opciones_usuarios)
            else:
                destinatario_sel = st.text_input("Escribir destinatario *", placeholder="Ej: Batalla / Sgto Batalla")
        with c_av2:
            mensaje_aviso = st.text_area("Mensaje / Orden de Trabajo *", placeholder="Ej: Cumplimentar informe fotográfico para el día lunes...")
            
        btn_emitir_aviso = st.form_submit_button("📤 Emitir Notificación")

    if btn_emitir_aviso:
        if not mensaje_aviso.strip() or not destinatario_sel.strip():
            st.error("Completá todos los campos obligatorios.")
        else:
            nuevo_id = len(df_avisos) + 1
            fecha_emision_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            nuevo_aviso_df = pd.DataFrame([{
                "id_aviso": str(nuevo_id),
                "destinatario": str(destinatario_sel).strip(),
                "mensaje": str(mensaje_aviso),
                "fecha_emision": str(fecha_emision_str),
                "estado": "PENDIENTE",
                "leido_por": "",
                "fecha_lectura": ""
            }])
            
            df_avisos = pd.concat([df_avisos, nuevo_aviso_df], ignore_index=True)
            guardar_avisos(df_avisos)
            st.success(f"✅ Notificación N° {nuevo_id} emitida para: `{destinatario_sel}`")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Control de Notificaciones y Acuses de Recibo")
    if df_avisos.empty:
        st.info("No se han emitido notificaciones aún.")
    else:
        st.dataframe(df_avisos, use_container_width=True)

    st.markdown("---")
    st.subheader("🔢 2. Control del Correlativo de Informes Técnicos (ITF)")
    st.write(f"El **último número asignado** fue el **{ultimo_itf_actual}**. El próximo informe se generará automáticamente con el N° **{ultimo_itf_actual + 1}**.")

    with st.form("form_itf"):
        nuevo_ultimo_itf = st.number_input(
            "Modificar manualmente el ÚLTIMO número de ITF asignado:",
            min_value=0,
            value=ultimo_itf_actual,
            step=1
        )
        btn_itf = st.form_submit_button("💾 Actualizar Contador ITF")

    if btn_itf:
        guardar_configuracion(nuevo_ultimo_itf)
        st.success(f"✅ Contador actualizado. El próximo informe será asignado con el N° {int(nuevo_ultimo_itf)+1:03d}-SFP-DG.CRIM.LA/{datetime.now().year}.")
        st.rerun()

# ==========================================
# 6. CAMBIAR CONTRASEÑA PERSONAL
# ==========================================
elif opcion_menu == "🔑 Cambiar Mi Contraseña":
    st.title("🔑 Gestión de Clave Personal")
    st.write(f"Actualización de credenciales para el efectivo: **{u_data['nombre']}** (`{u_data['usuario']}`)")

    with st.form("form_cambiar_clave"):
        clave_actual = st.text_input("Contraseña Actual", type="password")
        clave_nueva = st.text_input("Nueva Contraseña", type="password")
        clave_confirmar = st.text_input("Confirmar Nueva Contraseña", type="password")
        
        btn_cambiar = st.form_submit_button("💾 Guardar Nueva Contraseña")

    if btn_cambiar:
        if clave_actual != u_data['clave']:
            st.error("❌ La contraseña actual es incorrecta.")
        elif not clave_nueva:
            st.error("⚠️ La nueva contraseña no puede estar vacía.")
        elif clave_nueva != clave_confirmar:
            st.error("⚠️ La nueva contraseña y su confirmación no coinciden.")
        else:
            df_usuarios.loc[df_usuarios['usuario'] == u_data['usuario'], 'clave'] = clave_nueva
            guardar_usuarios(df_usuarios)
            st.session_state["usuario_data"]['clave'] = clave_nueva
            st.success("✅ Contraseña actualizada correctamente.")
            st.balloons()
