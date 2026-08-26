import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PIL import Image

st.set_page_config(page_title="Seguridad San José", page_icon="🥑", layout="centered")

# --- CONEXIÓN A DRIVE ---
@st.cache_resource
def conectar_drive():
    credenciales = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build('drive', 'v3', credentials=credenciales)

def obtener_ultimas_fotos(servicio, cantidad=5):
    # Busca imágenes en las carpetas compartidas con la cuenta de servicio
    resultados = servicio.files().list(
        q="mimeType='image/jpeg'",
        orderBy="createdTime desc",
        pageSize=cantidad,
        fields="files(id, name, createdTime)"
    ).execute()
    return resultados.get('files', [])

def descargar_imagen(servicio, file_id):
    request = servicio.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return Image.open(fh)

# --- SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["usuario"] == "admin" and st.session_state["clave"] == "utn2026":
            st.session_state["autenticado"] = True
            del st.session_state["clave"]
            del st.session_state["usuario"]
        else:
            st.session_state["autenticado"] = False

    if "autenticado" not in st.session_state:
        st.text_input("Usuario", key="usuario")
        st.text_input("Contraseña", type="password", key="clave")
        st.button("Ingresar", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["autenticado"]:
        st.error("🚫 Credenciales incorrectas.")
        return False
    return True

# --- PANEL DE CONTROL PRINCIPAL ---
st.markdown("<h1 style='text-align: center;'>🥑 Seguridad Perimetral San José</h1>", unsafe_allow_html=True)

if not st.session_state.get("autenticado", False):
    st.markdown("<h3 style='text-align: center;'>🔒 Acceso Restringido</h3>", unsafe_allow_html=True)

if check_password():
    st.success("Conexión segura establecida con el nodo Edge.")
    
    try:
        servicio = conectar_drive()
        st.info("✅ Enlace API con repositorio documental activo.")
        
        st.subheader("📷 Últimas Detecciones Vehiculares y Peatonales")
        
        with st.spinner('Extrayendo evidencias criptográficas...'):
            archivos = obtener_ultimas_fotos(servicio, 5)
            
        if not archivos:
            st.warning("El nodo no ha registrado fotografías recientes.")
        else:
            for archivo in archivos:
                # Formatear la fecha de la alerta
                fecha_limpia = archivo['createdTime'].replace("T", " ").split(".")[0]
                st.markdown(f"**Identificador:** `{archivo['name']}` | **Marca de tiempo:** `{fecha_limpia}`")
                
                # Descargar y mostrar la imagen
                img = descargar_imagen(servicio, archivo['id'])
                st.image(img, use_column_width=True)
                st.divider()

    except Exception as e:
        st.error(f"Fallo en la comunicación con el Backend: {e}")
