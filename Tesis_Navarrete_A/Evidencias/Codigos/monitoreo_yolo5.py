import cv2
import os
import time
import requests
import easyocr
import threading
import subprocess
from datetime import datetime
from ultralytics import YOLO
from picamera2 import Picamera2
from gpiozero import MotionSensor, OutputDevice

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOKEN = "8626887025:AAFdYomeBzMKQyYkmnFVxpKtaXqVtfajP0g"
CHAT_ID = "5682386608" 
BASE_DIR = "detecciones"
TIEMPO_SYNC_MINUTOS = 10

# ==========================================
# CONFIGURACIÓN DE HARDWARE
# ==========================================
print("Inicializando Hardware...")
pir = MotionSensor(17)
# active_high=False para tu relé de lógica inversa
foco = OutputDevice(27, active_high=False, initial_value=False)

# ==========================================
# INICIALIZACIÓN DE MODELOS E IA
# ==========================================
print("Cargando Inteligencia Artificial (YOLOv8 y EasyOCR)...")
model = YOLO('yolov8n.pt')
reader = easyocr.Reader(['es'])

print("Iniciando Cámara...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def obtener_directorios():
    """Crea y devuelve las rutas de carpetas por Mes y Día"""
    ahora = datetime.now()
    mes = ahora.strftime("%Y-%m")
    dia = ahora.strftime("%Y-%m-%d")
    
    dir_personas = os.path.join(BASE_DIR, mes, dia, "personas")
    dir_vehiculos = os.path.join(BASE_DIR, mes, dia, "vehiculos")
    
    os.makedirs(dir_personas, exist_ok=True)
    os.makedirs(dir_vehiculos, exist_ok=True)
    
    return dia, dir_personas, dir_vehiculos

def enviar_telegram(path, msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(path, 'rb') as f:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': msg}, files={'photo': f}, timeout=10)
        print("📧 Notificación de Telegram enviada.")
    except Exception as e:
        print(f"⚠️ Error Telegram: {e}")

def es_denoche():
    """Retorna True si es entre las 18:00 (6 PM) y las 05:59 AM"""
    hora_actual = datetime.now().hour
    return hora_actual >= 18 or hora_actual < 6

def sincronizar_drive():
    """Hilo en segundo plano que sincroniza con Google Drive cada 10 min usando Rclone"""
    while True:
        time.sleep(TIEMPO_SYNC_MINUTOS * 60)
        print(f"\n[☁️ Sincronización] Subiendo archivos a Google Drive...")
        try:
            # Comando de rclone para sincronizar la carpeta local con Drive
            subprocess.run(["rclone", "copy", BASE_DIR, "gdrive_tesis:detecciones"], check=True)
            print("[✅ Sincronización] Respaldo en la nube completado con éxito.")
        except Exception as e:
            print(f"[❌ Sincronización] Error al subir a Drive: {e}")

# ==========================================
# BUCLE PRINCIPAL DEL SISTEMA
# ==========================================
# Iniciar el hilo de sincronización en segundo plano
hilo_drive = threading.Thread(target=sincronizar_drive, daemon=True)
hilo_drive.start()

print("\n--- Sistema San José Activo y Monitoreando ---")

try:
    while True:
        # 1. Esperar detección de movimiento del sensor PIR
        pir.wait_for_motion()
        print("\n🚨 ¡Movimiento detectado!")
        
        # 2. Control de Iluminación Inteligente
        necesita_luz = es_denoche()
        if necesita_luz:
            print("🌙 Es de noche. Encendiendo reflector...")
            foco.on()
            time.sleep(1) # Esperar a que la cámara ajuste la exposición a la nueva luz
        
        # 3. Captura de imagen
        img_rgb = picam2.capture_array()
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        
        # 4. Apagar luz inmediatamente para ahorrar energía y no llamar la atención
        if necesita_luz:
            foco.off()
            print("💡 Reflector apagado.")
            
        # 5. Procesamiento con IA
        print("🧠 Analizando imagen...")
        results = model(img_rgb, conf=0.4, verbose=False)
        detectado = False
        
        # Crear estructura de carpetas del día actual
        dia_actual, ruta_personas, ruta_vehiculos = obtener_directorios()
        
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                ts = datetime.now().strftime("%H%M%S") # Solo la hora para el archivo (la fecha ya está en la carpeta)
                fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # --- LÓGICA PARA PERSONAS ---
                if label == 'person':
                    detectado = True
                    f_name = f"Persona_{ts}.jpg"
                    f_path = os.path.join(ruta_personas, f_name)
                    
                    cv2.imwrite(f_path, img_bgr)
                    print("👤 Persona detectada. Guardando...")
                    enviar_telegram(f_path, f"👤 ALERTA: Persona detectada en San José\n⏰ {fecha_hora}")

                # --- LÓGICA PARA VEHÍCULOS ---
                elif label in ['car', 'truck', 'motorcycle', 'bus']:
                    detectado = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Extraer placa (OCR)
                    placa_crop = img_rgb[y1:y2, x1:x2]
                    ocr_res = reader.readtext(placa_crop)
                    txt_placa = ocr_res[0][1] if ocr_res else "INDETERMINADA"
                    txt_placa = txt_placa.replace(" ", "")
                    
                    f_name = f"Vehiculo_{txt_placa}_{ts}.jpg"
                    f_path = os.path.join(ruta_vehiculos, f_name)
                    
                    cv2.imwrite(f_path, img_bgr)
                    print(f"🚗 Vehículo detectado (Placa: {txt_placa}). Guardando...")
                    
                    # Guardar placa en el archivo de texto del día
                    txt_log_path = os.path.join(ruta_vehiculos, f"Registro_Placas_{dia_actual}.txt")
                    with open(txt_log_path, "a") as txt_file:
                        txt_file.write(f"[{fecha_hora}] Tipo: {label} | Placa: {txt_placa}\n")
                    
                    enviar_telegram(f_path, f"🚗 VEHÍCULO: {label}\n🔢 PLACA: {txt_placa}\n⏰ {fecha_hora}")
        
        if not detectado:
            print("👻 Falsa alarma o sujeto no clasificado por la IA.")
            
        # 6. Tiempo de enfriamiento para evitar spam si el sujeto se queda en el área
        print("⏳ Pausa de seguridad (5 seg)...")
        time.sleep(5)
                
except KeyboardInterrupt:
    print("\n🛑 Finalizando sistema de forma segura...")
finally:
    foco.off() # Seguridad extra
    picam2.stop()
