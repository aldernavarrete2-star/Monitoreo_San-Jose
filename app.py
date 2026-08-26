import streamlit as st
import pandas as pd
import requests
import io
from PIL import Image
from google.oauth2 import service_account
import google.auth.transport.requests

st.set_page_config(page_title="Seguridad San José", page_icon="🥑", layout="centered")

CARPETA_RAIZ_ID = "1HRA_2wC9sEUHonaW_uCRe9R0YxACPZ6j"

# --- AUTENTICACIÓN SEGURA POR TOKEN HTTP ---
def obtener_token():
    credenciales = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    auth_request = google.auth.transport.requests.Request()
    credenciales.refresh(auth_request)
    return credenciales.token

def consultar_drive(url, params=None):
    """Realiza peticiones HTTP directas evitando el fallo de SSL sockets."""
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def listar_archivos(parent_id):
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{parent_id}' in parents and trashed=false",
        "orderBy": "name desc",
        "fields": "files(id, name, mimeType)"
    }
    data = consultar_drive(url, params)
    if data:
        return data.get('files', [])
    return []

def descargar_imagen(file_id):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    return None

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

# --- PANEL DE CONTROL ---
st.markdown("<h1 style='text-align: center;'>🥑 Seguridad Perimetral San José</h1>", unsafe_allow_html=True)

if check_password():
    st.success("Conexión segura establecida con el nodo Edge.")
    
    try:
        st.subheader("📁 Explorador de Evidencias Fotográficas")
        st.write("Navegación optimizada mediante API REST y tokens cifrados.")
        
        # 1. Seleccionar Mes
        meses = listar_archivos(CARPETA_RAIZ_ID)
        if meses:
            mes_seleccionado = st.selectbox("📅 Seleccione el Mes:", meses, format_func=lambda x: x['name'])
            
            # 2. Seleccionar Día
            dias = listar_archivos(mes_seleccionado['id'])
            if dias:
                dia_seleccionado = st.selectbox("📆 Seleccione el Día:", dias, format_func=lambda x: x['name'])
                
                # 3. Seleccionar Categoría
                categorias = listar_archivos(dia_seleccionado['id'])
                if categorias:
                    cat_seleccionada = st.selectbox("🔍 Seleccione la Categoría:", categorias, format_func=lambda x: x['name'])
                    
                    # 4. Mostrar fotos
                    fotos = listar_archivos(cat_seleccionada['id'])
                    
                    if fotos:
                        st.info(f"📸 Se encontraron {len(fotos)} registros en esta carpeta.")
                        for foto in fotos:
                            if "image" in foto['mimeType']:
                                st.markdown(f"**Archivo:** `{foto['name']}`")
                                with st.spinner('Descargando evidencia...'):
                                    img = descargar_imagen(foto['id'])
                                    if img:
                                        st.image(img, use_container_width=True)
                                    else:
                                        st.error("No se pudo descargar la imagen.")
                                st.divider()
                    else:
                        st.warning("No hay detecciones en esta carpeta.")
                else:
                    st.write("No hay categorías para este día.")
            else:
                st.write("No hay días registrados en este mes.")
        else:
            st.warning("El robot no encuentra la carpeta principal. Verifique permisos de compartición en Drive.")

    except Exception as e:
        st.error(f"Error crítico en el sistema: {e}")
