import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PIL import Image

st.set_page_config(page_title="Seguridad San José", page_icon="🥑", layout="centered")

# ID de tu carpeta principal "detecciones"
CARPETA_RAIZ_ID = "1HRA_2wC9sEUHonaW_uCRe9R0YxACPZ6j"

# --- CONEXIÓN A DRIVE ---
@st.cache_resource
def conectar_drive():
    credenciales = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build('drive', 'v3', credentials=credenciales)

# Se agrega Caché por 5 minutos (300 seg) para no saturar la red de Google
@st.cache_data(ttl=300, show_spinner=False)
def listar_archivos(_servicio, parent_id):
    """Busca archivos o carpetas dentro de un ID padre específico."""
    resultados = _servicio.files().list(
        q=f"'{parent_id}' in parents and trashed=false",
        orderBy="name desc",
        fields="files(id, name, mimeType)"
    ).execute()
    return resultados.get('files', [])

def descargar_imagen(servicio, file_id):
    """Descarga los bytes de la imagen y los convierte para mostrarlos."""
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
        st.markdown("<h2 style='text-align: center;'>🔒 Acceso Restringido</h2>", unsafe_allow_html=True)
        st.text_input("Usuario", key="usuario")
        st.text_input("Contraseña", type="password", key="clave")
        st.button("Ingresar al Sistema", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["autenticado"]:
        st.error("🚫 Credenciales incorrectas.")
        return False
    return True

# --- PANEL DE CONTROL PRINCIPAL ---
st.markdown("<h1 style='text-align: center;'>🥑 Seguridad Perimetral San José</h1>", unsafe_allow_html=True)

if check_password():
    st.success("Conexión segura establecida con el nodo Edge.")
    
    try:
        servicio = conectar_drive()
        
        st.subheader("📁 Explorador de Evidencias Fotográficas")
        st.write("Navegue por el árbol de directorios para visualizar las detecciones.")
        
        # 1. Seleccionar Mes
        meses = listar_archivos(servicio, CARPETA_RAIZ_ID)
        if meses:
            mes_seleccionado = st.selectbox("📅 Seleccione el Mes:", meses, format_func=lambda x: x['name'])
            
            # 2. Seleccionar Día
            dias = listar_archivos(servicio, mes_seleccionado['id'])
            if dias:
                dia_seleccionado = st.selectbox("📆 Seleccione el Día:", dias, format_func=lambda x: x['name'])
                
                # 3. Seleccionar Categoría
                categorias = listar_archivos(servicio, dia_seleccionado['id'])
                if categorias:
                    cat_seleccionada = st.selectbox("🔍 Seleccione la Categoría:", categorias, format_func=lambda x: x['name'])
                    
                    # 4. Mostrar las fotografías
                    fotos = listar_archivos(servicio, cat_seleccionada['id'])
                    
                    if fotos:
                        st.info(f"📸 Se encontraron {len(fotos)} registros en esta carpeta.")
                        for foto in fotos:
                            if "image" in foto['mimeType']:
                                st.markdown(f"**Archivo:** `{foto['name']}`")
                                with st.spinner('Descargando imagen encriptada...'):
                                    try:
                                        img = descargar_imagen(servicio, foto['id'])
                                        st.image(img, use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Error al cargar la imagen {foto['name']}: {e}")
                                st.divider()
                    else:
                        st.warning("No hay detecciones registradas en esta carpeta.")
                else:
                    st.write("No hay categorías creadas para este día.")
            else:
                st.write("No hay días registrados en este mes.")
        else:
            st.warning("El robot no encuentra la carpeta principal. Asegúrese de haber compartido la carpeta 'detecciones'.")

    except Exception as e:
        st.error(f"Fallo en la comunicación con el Backend: {e}")
