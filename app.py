import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="Seguridad San José", page_icon="🥑", layout="centered")

# --- CONEXIÓN A GOOGLE DRIVE ---
@st.cache_resource
def conectar_drive():
    credenciales = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build('drive', 'v3', credentials=credenciales)

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
        st.button("Ingresar", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["autenticado"]:
        st.error("🚫 Credenciales incorrectas.")
        return False
    return True

# --- PANEL DE CONTROL ---
if check_password():
    st.title("🥑 Panel de Seguridad - San José")
    st.success("Conexión segura establecida.")
    
    try:
        servicio_drive = conectar_drive()
        st.info("✅ Autenticación con Google Drive exitosa. El robot 'lector-nodo' está listo.")
        
        # Aquí programaremos la lectura de tu carpeta "detecciones"
        st.markdown("### ID de Carpeta Requerido")
        st.write("Para extraer las fotos, necesitamos el ID de la carpeta raíz.")
        
    except Exception as e:
        st.error(f"Error al conectar con Drive: {e}")