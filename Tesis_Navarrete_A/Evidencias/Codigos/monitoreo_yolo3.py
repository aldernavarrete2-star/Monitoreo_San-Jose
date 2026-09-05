import cv2
import os
import csv
import time
import requests
import easyocr
from datetime import datetime
from ultralytics import YOLO
from picamera2 import Picamera2

# --- CONFIGURACIÓN DE TELEGRAM ---
TOKEN = "8626887025:AAFdYomeBzMKQyYkmnFVxpKtaXqVtfajP0g"
CHAT_ID = "5682386608" 

# --- GESTIÓN DE DIRECTORIOS ---
base_dir = "detecciones"
for sub in ["personas", "vehiculos"]:
    os.makedirs(os.path.join(base_dir, sub), exist_ok=True)

# --- INICIALIZACIÓN DE MODELOS ---
print("Cargando IA...")
model = YOLO('yolov8n.pt')
reader = easyocr.Reader(['es'])
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

def enviar_telegram(path, msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(path, 'rb') as f:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': msg}, files={'photo': f})
        print("📧 Notificación enviada.")
    except Exception as e:
        print(f"Error Telegram: {e}")

print("--- Sistema San José Activo ---")

try:
    while True:
        img_rgb = picam2.capture_array()
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        results = model(img_rgb, conf=0.4, verbose=False)
        
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if label == 'person':
                    f_path = os.path.join(base_dir, "personas", f"P_{ts}.jpg")
                    cv2.imwrite(f_path, img_bgr)
                    enviar_telegram(f_path, f"👤 ALERTA: Persona detectada en San José\n⏰ {ts}")

                elif label in ['car', 'truck', 'motorcycle', 'bus']:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    placa_crop = img_rgb[y1:y2, x1:x2]
                    ocr_res = reader.readtext(placa_crop)
                    txt_placa = ocr_res[0][1] if ocr_res else "INDETERMINADA"
                    
                    f_name = f"{label}_{txt_placa}_{ts}.jpg".replace(" ", "_")
                    f_path = os.path.join(base_dir, "vehiculos", f_name)
                    cv2.imwrite(f_path, img_bgr)
                    
                    msg = f"🚗 VEHÍCULO: {label}\n🔢 PLACA: {txt_placa}\n⏰ {ts}"
                    enviar_telegram(f_path, msg)
                    
except KeyboardInterrupt:
    print("Finalizando...")
finally:
    picam2.stop()
