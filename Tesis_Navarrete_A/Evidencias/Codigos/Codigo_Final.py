import cv2 #procesamiento de imagen
import os  # crear archivos
import time  # maneja reloj para tareas
import requests # peticiones  tipo post get
import easyocr # motor de reconocieminto
import threading # permite multitarea
import subprocess #
from datetime import datetime # fecha
from ultralytics import YOLO #ia
from picamera2 import Picamera2   
from gpiozero import MotionSensor, OutputDevice

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOKEN = "8626887025:AAFdYomeBzMKQyYkmnFVxpKtaXqVtfajP0g"
CHAT_ID = "-5575877445 "  # grupo-5575877445  individual 5682386608
BASE_DIR = "detecciones"
TIEMPO_SYNC_MINUTOS = 10

# --- CONFIGURACIÓN DE CÁMARA Y RÁFAGA ---
ROTACION = cv2.ROTATE_180
NUM_FOTOS_RAFAGA = 3
TIEMPO_MINIMO_LUZ = 5 

# ==========================================
# CONFIGURACIÓN DE HARDWARE
# ==========================================
print("Inicializando Hardware...")
# [SENSOR PIR]: Se declara el pin 17 para el sensor que despierta el sistema.
pir = MotionSensor(17)
# [RELÉ / FOCO]: Se declara el pin 27 para el reflector LED. Inicia apagado (False).
foco = OutputDevice(27, active_high=False, initial_value=False)

# ==========================================
# INICIALIZACIÓN DE MODELOS E IA
# ==========================================
print("Cargando Inteligencia Artificial (YOLOv8 y EasyOCR)...")
model = YOLO('yolov8n.pt')
reader = easyocr.Reader(['es'])

# [INICIALIZACIÓN DE CÁMARA]: Se levanta la cámara usando el bus MIPI CSI-2.
# El formato RGB888 evita que la CPU pierda tiempo convirtiendo colores para la IA.
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
    # [ENVÍO A TELEGRAM]: Petición HTTP para enviar la evidencia (foto) y el texto de alerta.
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
    # [CONEXIÓN AL DRIVE]: Esta función corre en segundo plano continuamente.
    while True:
        time.sleep(TIEMPO_SYNC_MINUTOS * 60)
        print(f"\n[☁️ Sincronización] Subiendo archivos a Google Drive...")
        try:
            # Invoca a rclone (sistema operativo Linux) para empujar los archivos a la nube.
            subprocess.run(["rclone", "copy", BASE_DIR, "gdrive_tesis:detecciones"], check=True)
            print("[✅ Sincronización] Respaldo en la nube completado con éxito.")
        except Exception as e:
            print(f"[❌ Sincronización] Error al subir a Drive: {e}")

# ==========================================
# BUCLE PRINCIPAL DEL SISTEMA
# ==========================================
# [HILOS / THREADING]: Lanza la sincronización a Drive en paralelo para no congelar la vigilancia.
hilo_drive = threading.Thread(target=sincronizar_drive, daemon=True)
hilo_drive.start()

print("\n--- Sistema San José Activo y Monitoreando ---")

try:
    while True:
        # [DESPERTAR]: El sistema duerme consumiendo lo mínimo hasta que detecta calor/movimiento.
        pir.wait_for_motion()
        print("\n🚨 ¡Movimiento detectado! Iniciando ráfaga...")
        
        necesita_luz = es_denoche()
        tiempo_inicio_rafaga = time.time()
        
        # [ENCIENDE EL RELÉ]: Si es de noche, manda la señal al pin 27 para prender el foco de 12V.
        if necesita_luz:
            print("🌙 Es de noche. Encendiendo reflector...")
            foco.on()
            time.sleep(1) 
        
        dia_actual, ruta_personas, ruta_vehiculos = obtener_directorios()
        
        placas_vistas_ahorita = set()
        persona_vista_ahorita = False
        detectado = False
        
        for i in range(NUM_FOTOS_RAFAGA):
            print(f"📸 Capturando foto {i+1} de {NUM_FOTOS_RAFAGA}...")
            
            img_bgr_cruda = picam2.capture_array()
            
            # 1. Rotamos la imagen cruda
            img_bgr = cv2.rotate(img_bgr_cruda, ROTACION)
            
            # 2. Convertimos a RGB puro
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
            # [INFERENCIA IA]: Se evalúa la imagen en YOLO con un 40% de confianza mínima.
            results = model(img_rgb, conf=0.4, verbose=False)
            
            for r in results:
                
                boxes = r.boxes
                
                # --- PROCESAMIENTO DE VEHÍCULOS (Con mejoras OCR) ---
                # [DECISIÓN 1]: YOLO filtra y decide si en la foto hay algún tipo de vehículo.
                
                vehiculos = [b for b in boxes if model.names[int(b.cls[0])] in ['car', 'truck', 'motorcycle', 'bus']]
                
                if vehiculos:
                    detectado = True
                    vehiculo_principal = max(vehiculos, key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1]))
                    
                    x1, y1, x2, y2 = map(int, vehiculo_principal.xyxy[0])
                    label = model.names[int(vehiculo_principal.cls[0])]
                    ts = datetime.now().strftime("%H%M%S_%f")[:10]
                    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Recorte Inteligente (70% superior y sin 20% laterales)
                    ancho_carro = x2 - x1
                    margen_lateral = int(ancho_carro * 0.20)
                    x1_crop = x1 + margen_lateral
                    x2_crop = x2 - margen_lateral
                    y_inicio = y1 + int((y2 - y1) * 0.70) 
                    
                    placa_crop = img_rgb[y_inicio:y2, x1_crop:x2_crop]
                    
                    # 2. Zoom digital Cúbico (2.5x)
                    if placa_crop.size != 0:
                        placa_crop = cv2.resize(placa_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
                        
                        # 3. Escala de grises, corrección de luz (CLAHE) y Alto Contraste
                        placa_gray = cv2.cvtColor(placa_crop, cv2.COLOR_RGB2GRAY)
                        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
                        placa_gray = clahe.apply(placa_gray)
                        placa_gray = cv2.convertScaleAbs(placa_gray, alpha=2.5, beta=-15)
                        placa_gray = cv2.bilateralFilter(placa_gray, 11, 17, 17)
                        
                        # 4. Lectura OCR 
                        
                        ocr_res = reader.readtext(placa_gray, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
                        
                        textos_validos = []
                        for res in ocr_res:
                            texto = res[1].upper().replace(" ", "")
                            if "ECUADOR" not in texto and len(texto) >= 6:
                                textos_validos.append(texto)
                        
                        txt_placa = "-".join(textos_validos) if textos_validos else "INDETERMINADA"
                        
                        if txt_placa not in placas_vistas_ahorita:
                            f_name = f"Vehiculo_{txt_placa}_{ts}.jpg"
                            f_path = os.path.join(ruta_vehiculos, f_name)
                            
                            # Dibujar recuadro verde en la foto principal para Telegram
                            img_final = img_bgr.copy()
                            cv2.rectangle(img_final, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # [ALMACENAMIENTO LOCAL 1]: Guarda la fotografía en la memoria SD de la placa.
                            cv2.imwrite(f_path, img_final)
                            
                            txt_log_path = os.path.join(ruta_vehiculos, f"Registro_Placas_{dia_actual}.txt")
                            # [ALMACENAMIENTO LOCAL 2]: Escribe la placa extraída en la bitácora de texto (CSV).
                            with open(txt_log_path, "a") as txt_file:
                                txt_file.write(f"[{fecha_hora}] Tipo: {label} | Placa: {txt_placa}\n")
                            
                            # Llama a la función que contacta a Telegram
                            enviar_telegram(f_path, f"🚗 VEHÍCULO: {label}\n🔢 PLACA: {txt_placa}\n⏰ {fecha_hora}")
                            placas_vistas_ahorita.add(txt_placa)
                            print(f"🚗 Vehículo (Placa: {txt_placa}) guardado y enviado.")
                
                # --- PROCESAMIENTO DE PERSONAS ---
                # [DECISIÓN 2]: Si YOLO no vio ningún vehículo, entonces busca personas.
                if not detectado:  
                    personas = [b for b in boxes if model.names[int(b.cls[0])] == 'person']
                    if personas:
                        detectado = True
                        if not persona_vista_ahorita:
                            ts = datetime.now().strftime("%H%M%S")
                            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f_name = f"Persona_{ts}.jpg"
                            f_path = os.path.join(ruta_personas, f_name)
                            
                            # [ALMACENAMIENTO LOCAL]: Guarda foto de la persona en la SD.
                            cv2.imwrite(f_path, img_bgr)
                            enviar_telegram(f_path, f"👤 ALERTA: Persona detectada en San José\n⏰ {fecha_hora}")
                            persona_vista_ahorita = True
                            print("👤 Persona guardada y enviada.")
        
        tiempo_transcurrido = time.time() - tiempo_inicio_rafaga
        
        if necesita_luz:
            tiempo_restante = TIEMPO_MINIMO_LUZ - tiempo_transcurrido
            if tiempo_restante > 0:
                time.sleep(tiempo_restante)
            # [APAGA EL RELÉ]: Corta la energía del foco LED para ahorrar batería tras la captura.
            foco.off()
            print("💡 Reflector apagado tras iluminar la zona.")
            
        if not detectado:
            print("👻 Falsa alarma o sujeto no clasificado por la IA en ninguna foto.")
            
        print("⏳ Pausa de seguridad (5 seg)...")
        time.sleep(5)
                
except KeyboardInterrupt:
    print("\n🛑 Finalizando sistema de forma segura...")
finally:
    # [BLOQUE DE SEGURIDAD]: Si el programa se cae por un error, garantiza apagar el foco y liberar la cámara.
    foco.off() 
    picam2.stop()