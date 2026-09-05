# ==========================================
# 1. IMPORTACIÓN DE LIBRERÍAS
# ==========================================
import streamlit as st       # El framework principal para crear la página web.
import pandas as pd          # Manejo de datos .
import requests              # Permite hacer peticiones HTTP directas (GET/POST) a la nube.
import io                    # Maneja flujos de bytes en la memoria de la página.
from PIL import Image        # Procesa los bytes descargados para convertirlos en una imagen visible.
from google.oauth2 import service_account # Maneja la "Cuenta de Servicio" robot de Google.
import google.auth.transport.requests     # Renueva los tokens de seguridad de Google.

# Configuración básica de la pestaña del navegador (título y emoji).
st.set_page_config(page_title="Seguridad San José", page_icon="🥑", layout="centered")

# El ID único de la carpeta raíz "detecciones" en tu Google Drive.
CARPETA_RAIZ_ID = "1HRA_2wC9sEUHonaW_uCRe9R0YxACPZ6j"

# ==========================================
# 2. AUTENTICACIÓN SEGURA (CIBERSEGURIDAD)
# ==========================================
def obtener_token():
    # Toma la clave secreta guardada en st.secrets (para que no esté expuesta en GitHub).
    credenciales = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"] # Permiso de SOLO LECTURA.
    )
    # Solicita a Google Cloud que genere un Token temporal válido para esta sesión.
    auth_request = google.auth.transport.requests.Request()
    credenciales.refresh(auth_request)
    return credenciales.token # Retorna la "llave" temporal cifrada.

# ==========================================
# 3. COMUNICACIÓN CON GOOGLE DRIVE API REST
# ==========================================
def consultar_drive(url, params=None):
    """Realiza peticiones HTTP directas evitando el fallo de SSL sockets."""
    token = obtener_token()
    # Inyecta el Token temporal en la "cabecera" (header) de la petición HTTP.
    headers = {"Authorization": f"Bearer {token}"}
    # Hace una llamada GET a Google Drive.
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json() # Si Google responde OK (200), devuelve los datos en formato JSON.
    else:
        return None

def listar_archivos(parent_id):
    # Endpoint oficial de Google Drive para buscar archivos/carpetas.
    url = "https://www.googleapis.com/drive/v3/files"
    # Parámetros de búsqueda: busca dentro de la carpeta 'parent_id', ignorando la papelera, y ordena por nombre.
    params = {
        "q": f"'{parent_id}' in parents and trashed=false",
        "orderBy": "name desc",
        "fields": "files(id, name, mimeType)" # Solo pide ID, nombre y tipo (para no gastar datos de más).
    }
    data = consultar_drive(url, params)
    if data:
        return data.get('files', [])
    return []

def descargar_imagen(file_id):
    # Endpoint para descargar el archivo físico usando ?alt=media.
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    token = obtener_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Convierte los bytes descargados de internet en una imagen usando la librería PIL y la devuelve.
        return Image.open(io.BytesIO(response.content))
    return None

# ==========================================
# 4. SISTEMA DE LOGIN (MANEJO DE ESTADO)
# ==========================================
def check_password():
    def password_entered():
        # Compara lo que el usuario escribió con las credenciales quemadas (admin / utn2026).
        if st.session_state["usuario"] == "admin" and st.session_state["clave"] == "utn2026":
            st.session_state["autenticado"] = True # Guarda en la memoria que ya entró.
            # Borra las contraseñas de la memoria por seguridad.
            del st.session_state["clave"]
            del st.session_state["usuario"]
        else:
            st.session_state["autenticado"] = False

    # Si la variable "autenticado" no existe en la memoria, dibuja el formulario de login.
    if "autenticado" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔒 Acceso Restringido</h2>", unsafe_allow_html=True)
        st.text_input("Usuario", key="usuario")
        st.text_input("Contraseña", type="password", key="clave")
        st.button("Ingresar al Sistema", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["autenticado"]:
        st.error("🚫 Credenciales incorrectas.")
        return False
    return True # Si todo está correcto, devuelve True para dejarlo pasar al dashboard.

# ==========================================
# 5. RENDERIZADO DEL PANEL DE CONTROL (UI)
# ==========================================
st.markdown("<h1 style='text-align: center;'>🥑 Seguridad Perimetral San José</h1>", unsafe_allow_html=True)

# Llama a la función de login. Solo si devuelve True, ejecuta el resto del código.
if check_password():
    st.success("Conexión segura establecida con el nodo Edge.")
    
    try:
        st.subheader("📁 Explorador de Evidencias Fotográficas")
        st.write("Navegación optimizada mediante API REST y tokens cifrados.")
        
        # --- NAVEGACIÓN EN CASCADA ---
        # 1. Busca las carpetas de los MESES dentro de la carpeta raíz.
        meses = listar_archivos(CARPETA_RAIZ_ID)
        if meses:
            # Crea un menú desplegable con los meses encontrados.
            mes_seleccionado = st.selectbox("📅 Seleccione el Mes:", meses, format_func=lambda x: x['name'])
            
            # 2. Busca los DÍAS dentro de la carpeta del mes seleccionado.
            dias = listar_archivos(mes_seleccionado['id'])
            if dias:
                dia_seleccionado = st.selectbox("📆 Seleccione el Día:", dias, format_func=lambda x: x['name'])
                
                # 3. Busca las CATEGORÍAS (personas / vehiculos) dentro del día seleccionado.
                categorias = listar_archivos(dia_seleccionado['id'])
                if categorias:
                    cat_seleccionada = st.selectbox("🔍 Seleccione la Categoría:", categorias, format_func=lambda x: x['name'])
                    
                    # 4. Busca LAS FOTOS físicas dentro de la categoría.
                    fotos = listar_archivos(cat_seleccionada['id'])
                    
                    if fotos:
                        st.info(f"📸 Se encontraron {len(fotos)} registros en esta carpeta.")
                        # Recorre cada foto encontrada en un bucle.
                        for foto in fotos:
                            # Se asegura de que el archivo sea realmente una imagen (ignora txt o csv).
                            if "image" in foto['mimeType']:
                                st.markdown(f"**Archivo:** `{foto['name']}`")
                                # Muestra un círculo de carga mientras descarga la foto.
                                with st.spinner('Descargando evidencia...'):
                                    img = descargar_imagen(foto['id'])
                                    if img:
                                        # Dibuja la foto en la página ajustándola al ancho de la pantalla.
                                        st.image(img, use_container_width=True)
                                    else:
                                        st.error("No se pudo descargar la imagen.")
                                st.divider() # Dibuja una línea separadora entre fotos.
                    else:
                        st.warning("No hay detecciones en esta carpeta.")
                else:
                    st.write("No hay categorías para este día.")
            else:
                st.write("No hay días registrados en este mes.")
        else:
            st.warning("El robot no encuentra la carpeta principal. Verifique permisos de compartición en Drive.")

    except Exception as e:
        # Si algo falla gravemente (ej. caída de internet), atrapa el error para que la página no se rompa por completo.
        st.error(f"Error crítico en el sistema: {e}")