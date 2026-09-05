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

# --- CONFIGURACIÓN DE CÁMARA Y RÁFAGA ---
# Si la imagen está boca abajo usa: cv2.ROTATE_180
# Si está de lado usa: cv2.ROTATE_90_CLOCKWISE o cv2.ROTATE_90_COUNTERCLOCKWISE
ROTACION = cv2.ROTATE_90_CLOCKWISE 

NUM_FOTOS_RAFAGA = 3
TIEMPO_MINIMO_LUZ = 5 # Segundos que el foco se quedará encendido

# ==========================================
# CONFIGURACIÓN DE HARDWARE
# ==========================================
print("Inicializando Hardware...")
pir = MotionSensor(17)
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
    hora_actual = datetime.now().hour
    return hora_actual >= 18 or hora_actual < 6

def sincronizar_drive():
    while True:
        time.sleep(TIEMPO_SYNC_MINUTOS * 60)
        print(f"\n[☁️ Sincronización] Subiendo archivos a Google Drive...")
        try:
            subprocess.run(["rclone", "copy", BASE_DIR, "gdrive_tesis:detecciones"], check=True)
            print("[✅ Sincronización] Respaldo en la nube completado con éxito.")
        except Exception as e:
            print(f"[❌ Sincronización] Error al subir a Drive: {e}")

# ==========================================
# BUCLE PRINCIPAL DEL SISTEMA
# ==========================================
hilo_drive = threading.Thread(target=sincronizar_drive, daemon=True)
hilo_drive.start()

print("\n--- Sistema San José Activo y Monitoreando ---")

try:
    while True:
        pir.wait_for_motion()
        print("\n🚨 ¡Movimiento detectado! Iniciando ráfaga...")
        
        necesita_luz = es_denoche()
        tiempo_inicio_rafaga = time.time()
        
        if necesita_luz:
            print("🌙 Es de noche. Encendiendo reflector...")
            foco.on()
            time.sleep(1) # Esperar a que la cámara ajuste la exposición
        
        dia_actual, ruta_personas, ruta_vehiculos = obtener_directorios()
        
        # Filtros para no enviar mensajes repetidos durante esta misma ráfaga
        placas_vistas_ahorita = set()
        persona_vista_ahorita = False
        detectado = False
        
        for i in range(NUM_FOTOS_RAFAGA):
            print(f"📸 Capturando foto {i+1} de {NUM_FOTOS_RAFAGA}...")
            
            img_rgb_cruda = picam2.capture_array()
            
            # --- SOLUCIÓN DE ROTACIÓN ---
            img_rgb = cv2.rotate(img_rgb_cruda, ROTACION)
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            
            results = model(img_rgb, conf=0.4, verbose=False)
            
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    label = model.names[cls]
                    ts = datetime.now().strftime("%H%M%S")
                    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if label == 'person':
                        detectado = True
                        if not persona_vista_ahorita: # Solo manda telegram 1 vez por ráfaga
                            f_name = f"Persona_{ts}.jpg"
                            f_path = os.path.join(ruta_personas, f_name)
                            cv2.imwrite(f_path, img_bgr)
                            enviar_telegram(f_path, f"👤 ALERTA: Persona detectada en San José\n⏰ {fecha_hora}")
                            persona_vista_ahorita = True
                            print("👤 Persona guardada.")

                    elif label in ['car', 'truck', 'motorcycle', 'bus']:
                        detectado = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        placa_crop = img_rgb[y1:y2, x1:x2]
                        ocr_res = reader.readtext(placa_crop)
                        txt_placa = ocr_res[0][1] if ocr_res else "INDETERMINADA"
                        txt_placa = txt_placa.replace(" ", "")
                        
                        if txt_placa not in placas_vistas_ahorita:
                            f_name = f"Vehiculo_{txt_placa}_{ts}.jpg"
                            f_path = os.path.join(ruta_vehiculos, f_name)
                            cv2.imwrite(f_path, img_bgr)
                            
                            txt_log_path = os.path.join(ruta_vehiculos, f"Registro_Placas_{dia_actual}.txt")
                            with open(txt_log_path, "a") as txt_file:
                                txt_file.write(f"[{fecha_hora}] Tipo: {label} | Placa: {txt_placa}\n")
                            
                            enviar_telegram(f_path, f"🚗 VEHÍCULO: {label}\n🔢 PLACA: {txt_placa}\n⏰ {fecha_hora}")
                            placas_vistas_ahorita.add(txt_placa)
                            print(f"🚗 Vehículo (Placa: {txt_placa}) guardado.")
        
        # Evaluar cuánto tiempo tomó procesar la ráfaga
        tiempo_transcurrido = time.time() - tiempo_inicio_rafaga
        
        # Si la ráfaga terminó muy rápido, mantener la luz encendida hasta cumplir los 5 segundos
        if necesita_luz:
            tiempo_restante = TIEMPO_MINIMO_LUZ - tiempo_transcurrido
            if tiempo_restante > 0:
                time.sleep(tiempo_restante)
            foco.off()
            print("💡 Reflector apagado tras iluminar la zona.")
            
        if not detectado:
            print("👻 Falsa alarma o sujeto no clasificado por la IA en ninguna foto.")
            
        print("⏳ Pausa de seguridad (5 seg)...")
        time.sleep(5)
                
except KeyboardInterrupt:
    print("\n🛑 Finalizando sistema de forma segura...")
finally:
    foco.off() 
    picam2.stop()