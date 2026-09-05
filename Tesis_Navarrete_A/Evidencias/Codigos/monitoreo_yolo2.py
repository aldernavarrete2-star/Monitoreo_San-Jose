import cv2
import os
import csv
import time
import easyocr
from datetime import datetime
from ultralytics import YOLO
from picamera2 import Picamera2

# 1. Configuración de Carpetas
base_dir = "detecciones"
carpetas = ["personas", "vehiculos"]
for c in carpetas:
    os.makedirs(os.path.join(base_dir, c), exist_ok=True)

# 2. Inicialización de IA y Cámara
model = YOLO('yolov8n.pt')
reader = easyocr.Reader(['es']) # Lector de placas en español
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

print(f"--- Monitoreo Organizado en Sector San José Activo ---")

def registrar_placa(texto, tipo):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('registro_placas.csv', mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([fecha, tipo, texto])

try:
    while True:
        frame_rgb = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        # Inferencia con YOLO (confianza 0.3 para mejor detección en exterior)
        results = model(frame_rgb, conf=0.3, verbose=False)
        
        for r in results:
            for box in r.boxes:
                label = model.names[int(box.cls[0])]
                timestamp = datetime.now().strftime("%H%M%S")
                
                # CASO 1: PERSONAS
                if label == 'person':
                    path = os.path.join(base_dir, "personas", f"persona_{timestamp}.jpg")
                    cv2.imwrite(path, frame_bgr)
                    print("👤 Persona guardada en /personas")

                # CASO 2: VEHÍCULOS
                elif label in ['car', 'truck', 'motorcycle', 'bus']:
                    # Recortamos el área del vehículo para buscar la placa
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    crop = frame_rgb[y1:y2, x1:x2]
                    
                    # Intentar leer la placa en el recorte
                    resultado_ocr = reader.readtext(crop)
                    texto_placa = "No detectada"
                    if resultado_ocr:
                        texto_placa = resultado_ocr[0][1] # Extrae el texto con mayor confianza
                        registrar_placa(texto_placa, label)
                    
                    nombre_archivo = f"{label}_{texto_placa}_{timestamp}.jpg".replace(" ", "_")
                    path = os.path.join(base_dir, "vehiculos", nombre_archivo)
                    cv2.imwrite(path, frame_bgr)
                    print(f"🚗 {label} detectado (Placa: {texto_placa}) guardado en /vehiculos")

except KeyboardInterrupt:
    print("\nSistema detenido.")
finally:
    picam2.stop()
